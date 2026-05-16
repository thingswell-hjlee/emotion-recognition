"""
modules/voice_pipeline.py - 음성 분석 파이프라인 오케스트레이터

9단계 파이프라인:
1. microphone_capture → MIC_READY / MIC_ERROR
2. audio_preprocessing → AUDIO_BUFFERING
3. voice_activity_detection → VOICE_DETECTED / SILENCE_DETECTED / INSUFFICIENT_VOICE_DATA
4. feature_extraction → FEATURE_EXTRACTED / FEATURE_ERROR
5. voice_emotion_classification → EMOTION_CLASSIFIED / LOW_CONFIDENCE
6. confidence_filtering → FILTER_PASS / FILTER_REJECT
7. voice_emotion_average → VOICE_AVERAGE_READY / NO_DATA
8. voice_result_to_lstm → (controller에서 처리)
9. voice_result_to_ui → (controller에서 처리)

각 단계별 상태를 UI와 로그에 표시합니다.
무음 상태에서는 분류를 수행하지 않습니다.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config, DEFAULT_CONFIG
from modules.voice_activity_detector import VoiceActivityDetector, VADResult, VAD_VOICE_DETECTED, VAD_SILENCE_DETECTED, VAD_INSUFFICIENT_DATA
from modules.voice_features import VoiceFeatureExtractor, VoiceFeatures
from modules.voice_emotion import (
    create_voice_classifier, BaseVoiceEmotionClassifier, VoiceEmotionResult,
    VOICE_RESULT_OK, VOICE_RESULT_LOW_CONFIDENCE, VOICE_RESULT_SILENCE, VOICE_RESULT_INSUFFICIENT
)


# === 파이프라인 단계 상태 ===
STAGE_PENDING = "대기"
STAGE_RUNNING = "진행 중"
STAGE_DONE = "완료"
STAGE_SKIPPED = "건너뜀"
STAGE_ERROR = "오류"


@dataclass
class PipelineStage:
    """파이프라인 단계 상태"""
    name: str
    status: str = STAGE_PENDING
    detail: str = ""


@dataclass
class VoicePipelineState:
    """전체 파이프라인 실행 상태 (UI 표시용)"""
    stages: List[PipelineStage] = field(default_factory=list)
    current_stage: int = 0

    # 결과 데이터
    vad_result: Optional[VADResult] = None
    features: Optional[VoiceFeatures] = None
    emotion_result: Optional[VoiceEmotionResult] = None

    # 로그 메시지
    log_messages: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.stages:
            self.stages = [
                PipelineStage("마이크 대기"),
                PipelineStage("오디오 수집"),
                PipelineStage("음성 감지"),
                PipelineStage("특징 추출"),
                PipelineStage("감정 분류"),
                PipelineStage("신뢰도 필터"),
                PipelineStage("평균 계산"),
                PipelineStage("LSTM 전달"),
                PipelineStage("완료"),
            ]

    def set_stage(self, index: int, status: str, detail: str = ""):
        """단계 상태 업데이트"""
        if 0 <= index < len(self.stages):
            self.stages[index].status = status
            self.stages[index].detail = detail
            self.current_stage = index

    def add_log(self, message: str):
        self.log_messages.append(message)
        if len(self.log_messages) > 20:
            self.log_messages = self.log_messages[-20:]


class VoicePipeline:
    """
    음성 분석 파이프라인.
    마이크 입력 → VAD → 특징 추출 → 감정 분류 → 필터링
    각 단계에서 실패하면 이후 단계를 건너뜁니다.
    """

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self.vad = VoiceActivityDetector(config)
        self.feature_extractor = VoiceFeatureExtractor(config)
        self.classifier: Optional[BaseVoiceEmotionClassifier] = None
        self.state = VoicePipelineState()
        self._initialized = False

    def initialize(self) -> bool:
        """파이프라인 초기화"""
        # Feature extractor
        self.feature_extractor.initialize()

        # Classifier
        self.classifier = create_voice_classifier(self.config)

        self._initialized = True
        return True

    def process(self, audio: np.ndarray, sample_rate: int = 16000) -> VoiceEmotionResult:
        """
        오디오 데이터를 전체 파이프라인으로 처리합니다.

        Args:
            audio: float32 mono 오디오 버퍼
            sample_rate: 샘플레이트

        Returns:
            VoiceEmotionResult (성공 또는 실패 이유 포함)
        """
        self.state = VoicePipelineState()

        if not self._initialized:
            self.initialize()

        # Stage 0: 마이크 확인
        self.state.set_stage(0, STAGE_DONE, "MIC_READY")

        # Stage 1: 오디오 수집 확인
        if audio is None or len(audio) == 0:
            self.state.set_stage(1, STAGE_ERROR, "NO_AUDIO")
            self.state.add_log("[VOICE] SKIPPED reason=no_audio")
            return VoiceEmotionResult(
                emotion=None, status=VOICE_RESULT_SILENCE,
                reason="NO_AUDIO"
            )
        self.state.set_stage(1, STAGE_DONE, f"buffer={len(audio)} samples")

        # Stage 2: VAD (음성 활동 감지)
        vad_result = self.vad.analyze(audio, sample_rate)
        self.state.vad_result = vad_result
        self.state.add_log(
            f"[VOICE] LEVEL rms={vad_result.rms:.4f} peak={vad_result.peak:.3f} "
            f"dbfs={vad_result.dbfs:.1f} silence={'true' if not vad_result.is_valid else 'false'}"
        )

        if vad_result.status == VAD_SILENCE_DETECTED:
            self.state.set_stage(2, STAGE_DONE, "SILENCE_DETECTED")
            self._skip_remaining(3)
            self.state.add_log(f"[VOICE] SKIPPED reason=silence valid_seconds={vad_result.valid_seconds:.1f}")
            return VoiceEmotionResult(
                emotion=None, status=VOICE_RESULT_SILENCE,
                reason=f"SILENCE: rms={vad_result.rms:.4f} voice_ratio={vad_result.voice_ratio:.2f}"
            )

        if vad_result.status == VAD_INSUFFICIENT_DATA:
            self.state.set_stage(2, STAGE_DONE, "INSUFFICIENT_VOICE_DATA")
            self._skip_remaining(3)
            self.state.add_log(
                f"[VOICE] SKIPPED reason=insufficient valid_seconds={vad_result.valid_seconds:.1f} "
                f"ratio={vad_result.voice_ratio:.2f}"
            )
            return VoiceEmotionResult(
                emotion=None, status=VOICE_RESULT_INSUFFICIENT,
                reason=f"INSUFFICIENT: valid={vad_result.valid_seconds:.1f}s ratio={vad_result.voice_ratio:.2f}"
            )

        self.state.set_stage(2, STAGE_DONE, f"VOICE_DETECTED ratio={vad_result.voice_ratio:.2f}")

        # Stage 3: Feature 추출
        features = self.feature_extractor.extract(audio, sample_rate)
        self.state.features = features

        if not features.is_valid:
            self.state.set_stage(3, STAGE_ERROR, features.error or "FEATURE_ERROR")
            self._skip_remaining(4)
            self.state.add_log(f"[VOICE] FEATURE_ERROR: {features.error}")
            return VoiceEmotionResult(
                emotion=None, status=VOICE_RESULT_ERROR,
                reason=f"FEATURE_ERROR: {features.error}"
            )

        self.state.set_stage(3, STAGE_DONE, "FEATURE_EXTRACTED")
        self.state.add_log(f"[VOICE] FEATURES {features.to_log_string()}")

        # Stage 4: 감정 분류
        if self.classifier is None:
            self.state.set_stage(4, STAGE_ERROR, "CLASSIFIER_NOT_READY")
            self._skip_remaining(5)
            return VoiceEmotionResult(
                emotion=None, status=VOICE_RESULT_ERROR,
                reason="MODULE_DISABLED"
            )

        emotion_result = self.classifier.classify(features)
        self.state.emotion_result = emotion_result
        self.state.set_stage(4, STAGE_DONE, f"{emotion_result.status}")

        if emotion_result.emotion:
            self.state.add_log(
                f"[VOICE] RESULT emotion={emotion_result.emotion.dominant} "
                f"confidence={emotion_result.emotion.confidence:.2f} "
                f"mode={emotion_result.classifier_mode}"
            )

        # Stage 5: Confidence 필터
        tier = emotion_result.confidence_tier
        if tier == "discard":
            self.state.set_stage(5, STAGE_DONE, "FILTER_REJECT")
            self.state.add_log(f"[VOICE] FILTER status=discard weight=0.0")
        else:
            weight = {"strong": 1.0, "usable": 0.7, "low": 0.2}.get(tier, 0.0)
            self.state.set_stage(5, STAGE_DONE, f"FILTER_PASS tier={tier}")
            self.state.add_log(f"[VOICE] FILTER status={tier} weight={weight}")

        # Stage 6~8은 controller에서 처리
        self.state.set_stage(6, STAGE_PENDING, "controller에서 처리")
        self.state.set_stage(7, STAGE_PENDING, "controller에서 처리")
        self.state.set_stage(8, STAGE_PENDING, "완료 대기")

        return emotion_result

    def get_realtime_metrics(self, audio: np.ndarray) -> dict:
        """실시간 UI 표시용 메트릭 (빠른 계산)"""
        return self.vad.get_realtime_metrics(audio)

    def _skip_remaining(self, from_stage: int):
        """지정 단계 이후를 모두 건너뜀으로 표시"""
        for i in range(from_stage, len(self.state.stages)):
            self.state.set_stage(i, STAGE_SKIPPED)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def classifier_mode(self) -> str:
        if self.classifier:
            return self.classifier.mode_name
        return "disabled"
