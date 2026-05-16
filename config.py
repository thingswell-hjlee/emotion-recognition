"""
config.py - 전역 설정
Multimodal Emotion State Monitor의 모든 설정값을 관리합니다.

실행 모드:
- minimal: 카메라+UI+더미 분석 (첫 실행 권장, 의존성 최소)
- face: 웹캠 표정 분석 (DeepFace 필요)
- voice: 마이크 음성 분석 (librosa, sounddevice 필요)
- full: 표정+음성+LSTM+음성안내 전체 기능

성능 프로파일:
- low_power: 최소 부하, 일반 노트북 권장
- standard: 균형 잡힌 성능 (기본값)
- high_accuracy: 최대 정확도, 고사양 PC 권장
- debug: 모든 옵션 수동 제어
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


# === 실행 모드 ===
RUN_MODE_MINIMAL = "minimal"
RUN_MODE_FACE = "face"
RUN_MODE_VOICE = "voice"
RUN_MODE_FULL = "full"

VALID_RUN_MODES = [RUN_MODE_MINIMAL, RUN_MODE_FACE, RUN_MODE_VOICE, RUN_MODE_FULL]

# === 감정 카테고리 ===
EMOTIONS = [
    "neutral", "happy", "sad", "angry", "surprised",
    "fearful", "disgusted", "stressed", "calm"
]

# === 감정 이모지 매핑 ===
EMOTION_EMOJI: Dict[str, str] = {
    "neutral": "😐",
    "happy": "😊",
    "sad": "😢",
    "angry": "😠",
    "surprised": "😲",
    "fearful": "😨",
    "disgusted": "🤢",
    "stressed": "😰",
    "calm": "😌",
}

# === 감정 Valence (긍정/부정 가치) ===
EMOTION_VALENCE: Dict[str, float] = {
    "happy": 1.0,
    "calm": 0.7,
    "surprised": 0.2,
    "neutral": 0.0,
    "sad": -0.5,
    "disgusted": -0.6,
    "angry": -0.7,
    "fearful": -0.8,
    "stressed": -0.9,
}

# === DeepFace → 내부 감정 매핑 ===
DEEPFACE_TO_INTERNAL: Dict[str, str] = {
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
    "surprise": "surprised",
    "neutral": "neutral",
    "fear": "fearful",
    "disgust": "disgusted",
}


@dataclass
class Config:
    """전역 설정 데이터클래스"""

    # --- 실행 모드 ---
    run_mode: str = RUN_MODE_MINIMAL

    # --- 성능 프로파일 ---
    performance_profile: str = "standard"

    # --- 카메라 설정 ---
    camera_device_id: int = 0
    frame_width: int = 480
    frame_height: int = 360
    camera_fps: int = 15
    analysis_skip_frames: int = 5
    camera_retry_count: int = 3
    camera_enabled: bool = True

    # --- 마이크 설정 ---
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_chunk_size: int = 1024
    silence_threshold: float = 0.01
    silence_duration: float = 2.0
    audio_enabled: bool = False

    # --- 분석 설정 ---
    cycle_seconds: int = 10
    cycle_min: int = 3
    cycle_max: int = 15
    face_weight: float = 0.6
    voice_weight: float = 0.4
    analysis_mode: str = "integrated"
    face_analysis_enabled: bool = True
    audio_analysis_enabled: bool = False

    # --- 결과 안정화 ---
    smoothing_window: int = 4       # 이동평균 윈도우 크기
    confidence_threshold: float = 0.6  # 이 미만이면 low confidence

    # --- CPU 절약 ---
    cpu_saver: bool = False

    # --- LSTM 설정 ---
    lstm_sequence_length: int = 10
    lstm_min_data_points: int = 5
    lstm_model_path: str = "models/lstm_model.h5"
    lstm_n_features: int = 9

    # --- TTS (음성 안내) 설정 ---
    tts_enabled: bool = False
    tts_volume: int = 70
    tts_min_interval: int = 15
    tts_max_repeat: int = 3
    tts_language: str = "ko"

    # --- UI 설정 ---
    window_title: str = "Multimodal Emotion State Monitor"
    log_max_size: int = 50

    # --- 비교 임계값 ---
    comparison_stable_threshold: float = 0.05
    comparison_stress_threshold: float = 0.1
    comparison_volatile_threshold: float = 0.15

    # --- 파일 경로 ---
    log_file_path: str = "logs/app.log"
    config_file_path: str = "config.json"
    voice_model_path: str = "models/voice_emotion_model.pkl"

    # --- GPU 설정 ---
    force_cpu: bool = True
    suppress_tf_warnings: bool = True

    # === 프로파일 적용 ===

    def apply_profile(self, profile_name: str):
        """
        성능 프로파일을 적용합니다.
        프로파일 값으로 카메라/분석 설정을 업데이트합니다.
        """
        from performance_profiles import get_profile
        profile = get_profile(profile_name)

        self.performance_profile = profile_name
        self.frame_width, self.frame_height = profile.resolution
        self.camera_fps = profile.camera_fps
        self.cycle_seconds = profile.analysis_interval
        self.analysis_skip_frames = profile.analysis_skip_frames
        self.face_analysis_enabled = profile.face_analysis_enabled
        self.audio_analysis_enabled = profile.audio_analysis_enabled
        self.smoothing_window = profile.smoothing_window
        self.confidence_threshold = profile.confidence_threshold
        self.cpu_saver = profile.cpu_saver

    def apply_mode_defaults(self, run_mode: str):
        """
        실행 모드에 맞는 기본값을 적용합니다.
        모드 전환 시 호출됩니다.
        """
        self.run_mode = run_mode

        if run_mode == RUN_MODE_MINIMAL:
            self.camera_enabled = True
            self.audio_enabled = False
            self.face_analysis_enabled = False   # 더미 분석
            self.audio_analysis_enabled = False

        elif run_mode == RUN_MODE_FACE:
            self.camera_enabled = True
            self.audio_enabled = False
            self.face_analysis_enabled = True
            self.audio_analysis_enabled = False

        elif run_mode == RUN_MODE_VOICE:
            self.camera_enabled = False
            self.audio_enabled = True
            self.face_analysis_enabled = False
            self.audio_analysis_enabled = True

        elif run_mode == RUN_MODE_FULL:
            self.camera_enabled = True
            self.audio_enabled = True
            self.face_analysis_enabled = True
            self.audio_analysis_enabled = True

    def set_resolution(self, width: int, height: int):
        """해상도 변경"""
        self.frame_width = width
        self.frame_height = height

    # === 유효성 검증 ===

    def validate(self) -> bool:
        assert self.run_mode in VALID_RUN_MODES
        assert self.cycle_min <= self.cycle_seconds <= self.cycle_max
        assert 0 <= self.tts_volume <= 100
        return True

    def update_cycle(self, new_cycle: int):
        """주기 변경 (범위 제한 적용)"""
        self.cycle_seconds = max(self.cycle_min, min(self.cycle_max, new_cycle))

    def update_volume(self, new_volume: int):
        """볼륨 변경"""
        self.tts_volume = max(0, min(100, new_volume))

    # === 모드 기반 속성 ===

    @property
    def use_deepface(self) -> bool:
        """DeepFace 사용 여부"""
        return self.face_analysis_enabled and self.run_mode in (RUN_MODE_FACE, RUN_MODE_FULL)

    @property
    def use_voice(self) -> bool:
        """음성 분석 사용 여부"""
        return self.audio_analysis_enabled and self.run_mode in (RUN_MODE_VOICE, RUN_MODE_FULL)

    @property
    def use_lstm(self) -> bool:
        """LSTM 예측 사용 여부"""
        return self.run_mode == RUN_MODE_FULL

    @property
    def use_camera(self) -> bool:
        """카메라 사용 여부"""
        return self.camera_enabled and self.run_mode in (RUN_MODE_MINIMAL, RUN_MODE_FACE, RUN_MODE_FULL)


# === TensorFlow CPU 강제 설정 ===
def setup_tensorflow_cpu():
    """TensorFlow를 CPU 모드로 강제 설정 (Intel Arc Graphics 대응)"""
    try:
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
        os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    except Exception:
        pass


# === 기본 설정 인스턴스 ===
DEFAULT_CONFIG = Config()

# 앱 시작 시 TF CPU 설정 적용
if DEFAULT_CONFIG.force_cpu:
    setup_tensorflow_cpu()
