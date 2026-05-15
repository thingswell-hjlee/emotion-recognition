"""
controller.py - Core Controller (오케스트레이터)
전체 분석 파이프라인을 조율합니다.

핵심 설계 원칙:
- 어떤 모듈이 실패해도 앱 전체는 계속 실행
- 모든 외부 호출에 try/except 적용
- run_mode에 따라 필요한 모듈만 활성화
- graceful degradation: 기능 실패 시 UI에 상태만 표시
"""

import threading
import time
from datetime import datetime
from typing import Optional, Callable
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, DEFAULT_CONFIG, RUN_MODE_MINIMAL, RUN_MODE_FACE, RUN_MODE_VOICE, RUN_MODE_FULL
from utils.data_types import EmotionScores, AppState
from utils.timer import CycleTimer
from utils.logger import Logger


class EmotionController:
    """전체 감정 분석 파이프라인 오케스트레이터"""

    def __init__(self, config: Optional[Config] = None,
                 on_state_update: Optional[Callable[[AppState], None]] = None):
        self.config = config or Config()
        self.state = AppState()
        self._on_state_update = on_state_update
        self.logger = Logger(log_file=self.config.log_file_path, console=True)

        # 모듈 인스턴스 (lazy init)
        self._webcam = None
        self._face_classifier = None
        self._microphone = None
        self._voice_classifier = None
        self._integrator = None
        self._averager = None
        self._lstm_predictor = None
        self._comparator = None
        self._voice_feedback = None

        # 타이머
        self._timer = CycleTimer(
            cycle_seconds=self.config.cycle_seconds,
            on_cycle_complete=self._on_cycle_complete,
        )

        # 스레드
        self._face_thread: Optional[threading.Thread] = None
        self._running = False
        self._frame_count = 0
        self._lock = threading.Lock()

    # === 초기화 ===

    def initialize(self) -> bool:
        """
        모든 모듈 초기화.
        개별 모듈 실패 시에도 앱은 계속 실행됨.
        """
        self.logger.info(f"시스템 초기화 (모드: {self.config.run_mode})")
        self.state.run_mode = self.config.run_mode

        # Averager, Comparator는 항상 초기화 (순수 Python, 실패 없음)
        try:
            from modules.emotion_averager import EmotionAverager
            from modules.emotion_comparator import EmotionComparator
            self._averager = EmotionAverager()
            self._comparator = EmotionComparator(self.config)
        except Exception as e:
            self.logger.error(f"기본 모듈 초기화 실패: {e}")

        # 카메라 초기화
        if self.config.use_camera:
            self._init_camera()

        # 표정 분류기 초기화
        self._init_face_classifier()

        # 음성 모듈 초기화
        if self.config.use_voice:
            self._init_voice_modules()

        # LSTM 초기화
        self._init_lstm()

        # TTS 초기화
        self._init_voice_feedback()

        self.logger.info("시스템 초기화 완료")
        self._notify_state()
        return True

    def _init_camera(self):
        """카메라 초기화 (실패해도 앱 계속)"""
        try:
            from modules.webcam import WebcamCapture
            self._webcam = WebcamCapture(self.config)
            if self._webcam.open():
                self.state.face_status = "준비 완료"
                self.logger.info("웹캠 초기화 완료")
            else:
                self.state.face_status = "카메라 연결 실패"
                self.logger.warning("웹캠 열기 실패. 표정 분석이 비활성화됩니다.")
                self._webcam = None
        except Exception as e:
            self.state.face_status = f"카메라 오류: {e}"
            self.logger.error(f"카메라 초기화 실패: {e}")
            self._webcam = None

    def _init_face_classifier(self):
        """표정 분류기 초기화"""
        try:
            from modules.face_expression import FaceExpressionClassifier
            self._face_classifier = FaceExpressionClassifier(self.config)
            self._face_classifier.initialize()
            if self._face_classifier.init_error:
                self.logger.warning(self._face_classifier.init_error)
        except Exception as e:
            self.logger.error(f"표정 분류기 초기화 실패: {e}")
            self._face_classifier = None

    def _init_voice_modules(self):
        """음성 모듈 초기화 (마이크 + 분류기)"""
        # 마이크
        try:
            from modules.microphone import MicrophoneCapture
            self._microphone = MicrophoneCapture(self.config)
            if self._microphone.open():
                self.state.voice_status = "준비 완료"
                self.logger.info("마이크 초기화 완료")
            else:
                self.state.voice_status = "마이크 연결 실패"
                self.logger.warning("마이크 열기 실패. 음성 분석이 비활성화됩니다.")
                self._microphone = None
        except ImportError:
            self.state.voice_status = "sounddevice 미설치"
            self.logger.warning("sounddevice 미설치. 음성 분석 비활성화.")
            self._microphone = None
        except Exception as e:
            self.state.voice_status = f"마이크 오류: {e}"
            self.logger.error(f"마이크 초기화 실패: {e}")
            self._microphone = None

        # 음성 분류기
        try:
            from modules.voice_emotion import VoiceEmotionClassifier
            self._voice_classifier = VoiceEmotionClassifier(self.config)
            self._voice_classifier.initialize()
        except ImportError:
            self.logger.warning("librosa 미설치. 음성 감정 분류 비활성화.")
            self._voice_classifier = None
        except Exception as e:
            self.logger.error(f"음성 분류기 초기화 실패: {e}")
            self._voice_classifier = None

    def _init_lstm(self):
        """LSTM 예측기 초기화"""
        try:
            from modules.lstm_predictor import LSTMPredictor
            self._lstm_predictor = LSTMPredictor(self.config)
            self._lstm_predictor.initialize()
            if self._lstm_predictor.init_error:
                self.logger.warning(self._lstm_predictor.init_error)
            self.state.lstm_status = f"준비 완료 ({self._lstm_predictor.mode_name})"
        except Exception as e:
            self.logger.error(f"LSTM 초기화 실패: {e}")
            self._lstm_predictor = None
            self.state.lstm_status = "비활성화"

    def _init_voice_feedback(self):
        """음성 안내 초기화"""
        try:
            from modules.voice_feedback import VoiceFeedback
            self._voice_feedback = VoiceFeedback(self.config)
            self._voice_feedback.initialize()
            if self._voice_feedback.init_error:
                self.logger.warning(self._voice_feedback.init_error)

            # TTS-마이크 간섭 방지
            if self._microphone and self._voice_feedback:
                self._voice_feedback.set_callbacks(
                    on_start=lambda: self._microphone.set_tts_playing(True),
                    on_end=lambda: self._microphone.set_tts_playing(False),
                )
        except Exception as e:
            self.logger.error(f"TTS 초기화 실패: {e}")
            self._voice_feedback = None

    # === 시작/정지 ===

    def start(self):
        """분석 파이프라인 시작"""
        if self._running:
            return

        self._running = True
        self.state.is_running = True
        self.state.add_log("분석 시작")

        # 카메라 스레드
        if self._webcam is not None:
            self.state.camera_active = True
            self._face_thread = threading.Thread(
                target=self._face_analysis_loop, daemon=True
            )
            self._face_thread.start()

        # 마이크
        if self._microphone is not None:
            try:
                self._microphone.start_capture()
                self.state.microphone_active = True
            except Exception as e:
                self.logger.error(f"마이크 캡처 시작 실패: {e}")
                self.state.voice_status = "캡처 실패"

        # 타이머
        self._timer.start()

        self.logger.info(f"분석 시작 (모드: {self.config.run_mode}, 주기: {self.config.cycle_seconds}초)")
        self._notify_state()

    def stop(self):
        """분석 파이프라인 정지"""
        self._running = False
        self.state.is_running = False

        self._timer.stop()

        self.state.camera_active = False
        if self._face_thread and self._face_thread.is_alive():
            self._face_thread.join(timeout=3.0)

        if self._microphone:
            try:
                self._microphone.stop_capture()
            except Exception:
                pass
        self.state.microphone_active = False

        self.state.add_log("분석 정지")
        self.logger.info("분석 정지")
        self._notify_state()

    def cleanup(self):
        """모든 리소스 해제"""
        self.stop()
        if self._webcam:
            try:
                self._webcam.release()
            except Exception:
                pass
        if self._microphone:
            try:
                self._microphone.close()
            except Exception:
                pass
        self.logger.info("리소스 해제 완료")

    # === 설정 변경 ===

    def update_cycle(self, new_cycle: int):
        self.config.update_cycle(new_cycle)
        self.state.cycle_seconds = self.config.cycle_seconds
        self._timer.reset(self.config.cycle_seconds)
        if self._microphone:
            try:
                self._microphone.update_cycle(self.config.cycle_seconds)
            except Exception:
                pass
        if self._averager:
            self._averager.reset()
        if self._lstm_predictor:
            self._lstm_predictor.reset()
        self.state.add_log(f"주기 변경: {self.config.cycle_seconds}초")
        self._notify_state()

    def update_volume(self, new_volume: int):
        self.config.update_volume(new_volume)
        self.state.volume = self.config.tts_volume
        if self._voice_feedback:
            self._voice_feedback.set_volume(self.config.tts_volume)

    def update_voice_feedback(self, enabled: bool):
        self.config.tts_enabled = enabled
        self.state.voice_feedback_enabled = enabled
        if self._voice_feedback:
            self._voice_feedback.set_enabled(enabled)

    def update_camera_index(self, new_index: int):
        """카메라 인덱스 변경"""
        was_running = self._running
        if was_running:
            self.stop()
        self.config.camera_device_id = new_index
        if self._webcam:
            try:
                self._webcam.release()
            except Exception:
                pass
        self._init_camera()
        if was_running:
            self.start()
        self._notify_state()

    def update_run_mode(self, new_mode: str):
        """실행 모드 변경"""
        was_running = self._running
        if was_running:
            self.stop()
        self.config.run_mode = new_mode
        self.state.run_mode = new_mode
        self.initialize()
        if was_running:
            self.start()
        self.state.add_log(f"실행 모드 변경: {new_mode}")
        self._notify_state()

    # === 분석 루프 ===

    def _face_analysis_loop(self):
        """표정 분석 루프 (별도 스레드)"""
        retry_count = 0

        while self._running and self.state.camera_active:
            try:
                success, frame = self._webcam.read_frame()
                if not success:
                    retry_count += 1
                    if retry_count >= self.config.camera_retry_count:
                        self.state.face_status = "프레임 읽기 실패"
                        time.sleep(1.0)
                        retry_count = 0
                    time.sleep(0.1)
                    continue

                retry_count = 0
                self._frame_count += 1

                # 프레임 스킵
                if self._frame_count % self.config.analysis_skip_frames != 0:
                    time.sleep(0.01)
                    continue

                # 얼굴 감지
                faces = self._webcam.detect_faces(frame)
                if not faces:
                    self.state.face_status = "얼굴 미감지"
                    time.sleep(0.05)
                    continue

                self.state.face_status = "분석 중"
                largest = self._webcam.get_largest_face(faces)
                face_img = self._webcam.crop_face(frame, largest)
                if face_img is None:
                    continue

                # 표정 분류
                face_result = None
                if self._face_classifier:
                    face_result = self._face_classifier.classify(face_img)

                if face_result is None:
                    continue

                # 결과 처리
                with self._lock:
                    self.state.current_emotion = face_result
                    self.state.face_status = "사용 중"
                    if self._averager:
                        self._averager.add_result(face_result)

                self._notify_state()
                time.sleep(0.02)

            except Exception as e:
                self.logger.error(f"표정 분석 루프 오류: {e}")
                time.sleep(0.5)

    def _on_cycle_complete(self):
        """주기 완료 콜백"""
        try:
            with self._lock:
                self._process_cycle_end()
        except Exception as e:
            self.logger.error(f"주기 처리 오류: {e}")

    def _process_cycle_end(self):
        """주기 종료 처리"""
        # ① 음성 분석 (voice mode)
        if self.config.use_voice and self._microphone and self._voice_classifier:
            try:
                if not self._microphone.is_silence():
                    audio = self._microphone.get_buffer()
                    voice_result = self._voice_classifier.classify(
                        audio, self.config.audio_sample_rate
                    )
                    if voice_result and self._averager:
                        self._averager.add_result(voice_result)
                        self.state.voice_status = "분석 완료"
                else:
                    self.state.voice_status = "음성 미감지"
            except Exception as e:
                self.logger.error(f"음성 분석 실패: {e}")
                self.state.voice_status = "분석 오류"

        # ② 감정 평균 계산
        avg = None
        if self._averager:
            try:
                avg = self._averager.calculate_average()
            except Exception as e:
                self.logger.error(f"평균 계산 실패: {e}")

        if avg:
            self.state.average_emotion = avg
            self.state.add_log(f"평균 감정: {avg.dominant} ({avg.confidence:.0%})")
            self.logger.emotion("average", {
                "dominant": avg.dominant,
                "confidence": avg.confidence,
                "scores": avg.scores,
            })

            # ③ LSTM 예측
            if self._lstm_predictor:
                try:
                    self._lstm_predictor.add_data_point(avg.scores)
                    if self._lstm_predictor.is_ready:
                        predicted = self._lstm_predictor.predict()
                        if predicted:
                            self.state.predicted_emotion = predicted
                            self.state.lstm_status = f"예측 중 ({self._lstm_predictor.mode_name})"
                            self.state.add_log(f"예측: {predicted.dominant} ({predicted.confidence:.0%})")

                            # ④ 비교
                            if self._comparator:
                                label, magnitude = self._comparator.compare(avg.scores, predicted.scores)
                                self.state.comparison_label = label
                                self.state.comparison_magnitude = magnitude
                                self.state.add_log(f"비교: {label} ({magnitude:.2f})")
                    else:
                        self.state.lstm_status = f"데이터 수집 중 ({self._lstm_predictor.data_count}/{self.config.lstm_min_data_points})"
                except Exception as e:
                    self.logger.error(f"LSTM 예측 실패: {e}")
                    self.state.lstm_status = "예측 오류"

            # ⑤ 음성 안내
            if self._voice_feedback and self.config.tts_enabled:
                try:
                    message = self._voice_feedback.speak(
                        avg.dominant, self.state.comparison_label
                    )
                    if message:
                        self.state.add_log(f"음성 안내: {message}")
                except Exception as e:
                    self.logger.error(f"TTS 실패: {e}")
        else:
            self.state.add_log("데이터 부족")

        # 주기 리셋
        if self._averager:
            self._averager.reset()
        if self._microphone:
            try:
                self._microphone.clear_buffer()
            except Exception:
                pass

        self._notify_state()

    def _notify_state(self):
        """UI 콜백 호출"""
        if self._on_state_update:
            try:
                self._on_state_update(self.state)
            except Exception:
                pass
