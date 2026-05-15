"""
controller.py - Core Controller (오케스트레이터)
전체 분석 파이프라인을 조율하고, 주기 타이머를 관리하며,
모듈 간 데이터 흐름을 제어합니다.
"""

import threading
import time
from datetime import datetime
from typing import Optional, Callable

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, DEFAULT_CONFIG
from utils.data_types import EmotionScores, AppState
from utils.timer import CycleTimer
from utils.logger import Logger
from modules.webcam import WebcamCapture
from modules.face_expression import FaceExpressionClassifier
from modules.microphone import MicrophoneCapture
from modules.voice_emotion import VoiceEmotionClassifier
from modules.emotion_integrator import EmotionIntegrator
from modules.emotion_averager import EmotionAverager
from modules.lstm_predictor import LSTMPredictor
from modules.emotion_comparator import EmotionComparator
from modules.voice_feedback import VoiceFeedback


class EmotionController:
    """전체 감정 분석 파이프라인 오케스트레이터"""

    def __init__(self, config: Optional[Config] = None,
                 on_state_update: Optional[Callable[[AppState], None]] = None):
        """
        Args:
            config: 설정 (None이면 기본값)
            on_state_update: 상태 변경 시 호출할 콜백 (UI 업데이트용)
        """
        self.config = config or Config()
        self.state = AppState()
        self._on_state_update = on_state_update

        # 모듈 인스턴스
        self.webcam = WebcamCapture(self.config)
        self.face_classifier = FaceExpressionClassifier()
        self.microphone = MicrophoneCapture(self.config)
        self.voice_classifier = VoiceEmotionClassifier(self.config)
        self.integrator = EmotionIntegrator(self.config)
        self.averager = EmotionAverager()
        self.lstm_predictor = LSTMPredictor(self.config)
        self.comparator = EmotionComparator(self.config)
        self.voice_feedback = VoiceFeedback(self.config)
        self.logger = Logger(log_file=self.config.log_file_path, console=True)

        # 타이머
        self.timer = CycleTimer(
            cycle_seconds=self.config.cycle_seconds,
            on_cycle_complete=self._on_cycle_complete,
        )

        # 스레드
        self._face_thread: Optional[threading.Thread] = None
        self._running = False
        self._frame_count = 0
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        """모든 모듈 초기화"""
        self.logger.info("시스템 초기화 중...")
        success = True

        # 분석 모드에 따라 필요한 모듈만 초기화
        mode = self.config.analysis_mode

        if mode in ("face_only", "integrated"):
            if self.webcam.open():
                self.state.face_status = "준비 완료"
                self.logger.info("웹캠 초기화 완료")
            else:
                self.state.face_status = "사용 불가"
                self.logger.warning("웹캠 초기화 실패")
                if mode == "face_only":
                    success = False

            self.face_classifier.initialize()

        if mode in ("voice_only", "integrated"):
            if self.microphone.open():
                self.state.voice_status = "준비 완료"
                self.logger.info("마이크 초기화 완료")
            else:
                self.state.voice_status = "사용 불가"
                self.logger.warning("마이크 초기화 실패")
                if mode == "voice_only":
                    success = False

            self.voice_classifier.initialize()

        # LSTM / TTS 초기화
        self.lstm_predictor.initialize()
        self.voice_feedback.initialize()

        # TTS-마이크 간섭 방지 콜백
        self.voice_feedback.set_callbacks(
            on_start=lambda: self.microphone.set_tts_playing(True),
            on_end=lambda: self.microphone.set_tts_playing(False),
        )

        self.logger.info("시스템 초기화 완료")
        self._notify_state()
        return success

    def start(self):
        """분석 파이프라인 시작"""
        if self._running:
            return

        self._running = True
        self.state.is_running = True
        self.state.add_log("분석 시작")

        mode = self.config.analysis_mode

        # 카메라 시작
        if mode in ("face_only", "integrated") and self.webcam.is_opened:
            self.state.camera_active = True
            self._face_thread = threading.Thread(
                target=self._face_analysis_loop, daemon=True
            )
            self._face_thread.start()

        # 마이크 시작
        if mode in ("voice_only", "integrated") and self.microphone.is_opened:
            self.microphone.start_capture()
            self.state.microphone_active = True

        # 타이머 시작
        self.timer.start()

        self.logger.info(f"분석 시작 (모드: {mode}, 주기: {self.config.cycle_seconds}초)")
        self._notify_state()

    def stop(self):
        """분석 파이프라인 정지"""
        self._running = False
        self.state.is_running = False

        # 타이머 정지
        self.timer.stop()

        # 카메라 정지
        self.state.camera_active = False
        if self._face_thread and self._face_thread.is_alive():
            self._face_thread.join(timeout=2.0)

        # 마이크 정지
        self.microphone.stop_capture()
        self.state.microphone_active = False

        self.state.add_log("분석 정지")
        self.logger.info("분석 정지")
        self._notify_state()

    def cleanup(self):
        """모든 리소스 해제"""
        self.stop()
        self.webcam.release()
        self.microphone.close()
        self.logger.info("리소스 해제 완료")

    # === 설정 변경 ===

    def update_cycle(self, new_cycle: int):
        """분석 주기 변경"""
        self.config.update_cycle(new_cycle)
        self.state.cycle_seconds = self.config.cycle_seconds
        self.timer.reset(self.config.cycle_seconds)
        self.microphone.update_cycle(self.config.cycle_seconds)
        self.averager.reset()
        self.lstm_predictor.reset()
        self.state.add_log(f"주기 변경: {self.config.cycle_seconds}초")
        self._notify_state()

    def update_volume(self, new_volume: int):
        """볼륨 변경"""
        self.config.update_volume(new_volume)
        self.state.volume = self.config.tts_volume
        self.voice_feedback.set_volume(self.config.tts_volume)

    def update_mode(self, new_mode: str):
        """분석 모드 변경"""
        was_running = self._running
        if was_running:
            self.stop()

        self.config.analysis_mode = new_mode
        self.state.analysis_mode = new_mode
        self.averager.reset()
        self.state.add_log(f"분석 모드 변경: {new_mode}")

        if was_running:
            self.initialize()
            self.start()

        self._notify_state()

    def update_voice_feedback(self, enabled: bool):
        """음성 안내 ON/OFF"""
        self.config.tts_enabled = enabled
        self.state.voice_feedback_enabled = enabled
        self.voice_feedback.set_enabled(enabled)

    # === 내부 루프 ===

    def _face_analysis_loop(self):
        """표정 분석 루프 (별도 스레드)"""
        while self._running and self.state.camera_active:
            success, frame = self.webcam.read_frame()
            if not success:
                time.sleep(0.033)
                continue

            self._frame_count += 1

            # 프레임 스킵
            if self._frame_count % self.config.analysis_skip_frames != 0:
                time.sleep(0.01)
                continue

            # 얼굴 감지
            faces = self.webcam.detect_faces(frame)
            if not faces:
                self.state.face_status = "얼굴 미감지"
                time.sleep(0.033)
                continue

            self.state.face_status = "분석 중"
            largest = self.webcam.get_largest_face(faces)

            # 얼굴 크롭
            face_img = self.webcam.crop_face(frame, largest)
            if face_img is None:
                continue

            # 표정 분류
            face_result = self.face_classifier.classify(face_img)
            if face_result is None:
                continue

            # 통합 처리
            with self._lock:
                voice_result = None
                if (self.config.analysis_mode == "integrated" and
                        not self.microphone.is_silence()):
                    audio = self.microphone.get_buffer()
                    voice_result = self.voice_classifier.classify(
                        audio, self.config.audio_sample_rate
                    )

                integrated = self.integrator.integrate(
                    face_result, voice_result, self.config.analysis_mode
                )

                if integrated:
                    self.state.current_emotion = integrated
                    self.averager.add_result(integrated)
                    self.state.face_status = "사용 중"

            self._notify_state()
            time.sleep(0.01)

    def _on_cycle_complete(self):
        """주기 완료 시 호출 (타이머 콜백)"""
        with self._lock:
            self._process_cycle_end()

    def _process_cycle_end(self):
        """주기 종료 처리: 평균→LSTM→비교→음성안내→UI"""
        # ① 음성 분석 (voice_only 모드일 때)
        if self.config.analysis_mode == "voice_only" and self.microphone.is_opened:
            if not self.microphone.is_silence():
                audio = self.microphone.get_buffer()
                voice_result = self.voice_classifier.classify(
                    audio, self.config.audio_sample_rate
                )
                if voice_result:
                    integrated = self.integrator.integrate(
                        None, voice_result, "voice_only"
                    )
                    if integrated:
                        self.state.current_emotion = integrated
                        self.averager.add_result(integrated)
            else:
                self.state.voice_status = "음성 미감지"

        # ② 감정 평균 계산
        avg = self.averager.calculate_average()
        if avg:
            self.state.average_emotion = avg
            self.state.add_log(f"평균 감정: {avg.dominant} ({avg.confidence:.0%})")

            self.logger.emotion("average", {
                "dominant": avg.dominant,
                "confidence": avg.confidence,
                "scores": avg.scores,
            })

            # ③ LSTM 예측
            self.lstm_predictor.add_data_point(avg.scores)

            if self.lstm_predictor.is_ready:
                predicted = self.lstm_predictor.predict()
                if predicted:
                    self.state.predicted_emotion = predicted
                    self.state.lstm_status = "예측 중"
                    self.state.add_log(
                        f"LSTM 예측: {predicted.dominant} ({predicted.confidence:.0%})"
                    )

                    # ④ 평균 vs 예측 비교
                    label, magnitude = self.comparator.compare(
                        avg.scores, predicted.scores
                    )
                    self.state.comparison_label = label
                    self.state.comparison_magnitude = magnitude
                    self.state.add_log(f"비교 결과: {label} (변화폭: {magnitude:.2f})")

                    # ⑤ 음성 안내
                    message = self.voice_feedback.speak(avg.dominant, label)
                    if message:
                        self.state.add_log(f"음성 안내: {message}")
                else:
                    self.state.lstm_status = "예측 실패"
            else:
                self.state.lstm_status = f"데이터 수집 중 ({self.lstm_predictor.data_count}/{self.config.lstm_min_data_points})"
                # 데이터 부족해도 음성 안내는 제공
                message = self.voice_feedback.speak(avg.dominant)
                if message:
                    self.state.add_log(f"음성 안내: {message}")
        else:
            self.state.add_log("데이터 부족: 분석 결과 없음")

        # 주기 리셋
        self.averager.reset()
        self.microphone.clear_buffer()

        self._notify_state()

    def _notify_state(self):
        """UI 상태 업데이트 콜백 호출"""
        if self._on_state_update:
            try:
                self._on_state_update(self.state)
            except Exception:
                pass
