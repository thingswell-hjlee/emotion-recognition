"""
controller.py - Core Controller (오케스트레이터)
전체 분석 파이프라인을 조율합니다.

핵심 설계 원칙:
- 어떤 모듈이 실패해도 앱 전체는 계속 실행
- 모든 외부 호출에 try/except 적용
- run_mode에 따라 필요한 모듈만 활성화
- graceful degradation: 기능 실패 시 UI에 상태만 표시
- 슬라이더 값 변경 시 전체 재초기화 없이 hot-update 지원
- EmotionSmoother로 결과 안정화
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
from utils.smoothing import EmotionSmoother


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
        self._averager = None
        self._lstm_predictor = None
        self._comparator = None
        self._voice_feedback = None

        # 결과 안정화 (smoothing)
        self._smoother = EmotionSmoother(
            window_size=self.config.smoothing_window,
            confidence_threshold=self.config.confidence_threshold,
        )

        # 새 음성 파이프라인 + 분리된 평균 계산
        self._voice_pipeline = None
        self._voice_averager = None

        # STT 엔진
        self._stt_engine = None
        self._stt_history = None

        # 라이브 프리뷰용 최신 프레임
        self._latest_frame = None

        # 타이머
        self._timer = CycleTimer(
            cycle_seconds=self.config.cycle_seconds,
            on_cycle_complete=self._on_cycle_complete,
        )

        # 스레드
        self._face_thread: Optional[threading.Thread] = None
        self._running = False
        self._cleaned_up = False
        self._frame_count = 0
        self._lock = threading.Lock()

    # ================================================================
    # 초기화
    # ================================================================

    def initialize(self) -> bool:
        """
        모든 모듈 초기화.
        개별 모듈 실패 시에도 앱은 계속 실행됨.
        """
        self.logger.info(f"시스템 초기화 (모드: {self.config.run_mode}, 프로파일: {self.config.performance_profile})")
        self.state.run_mode = self.config.run_mode

        # Averager, Comparator (순수 Python, 실패 없음)
        try:
            from modules.emotion_comparator import EmotionComparator
            from modules.voice_averager import VoiceAverager
            self._comparator = EmotionComparator(self.config)
            # voice_averager는 모든 모드에서 사용 (face 결과도 관리)
            self._voice_averager = VoiceAverager(self.config)
        except Exception as e:
            self.logger.error(f"기본 모듈 초기화 실패: {e}")

        # 카메라
        if self.config.use_camera:
            self._init_camera()

        # 표정 분류기
        self._init_face_classifier()

        # 음성 모듈
        if self.config.use_voice:
            self._init_voice_modules()

        # LSTM
        self._init_lstm()

        # TTS
        self._init_voice_feedback()

        # STT
        self._init_stt()

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
                self.logger.warning("웹캠 열기 실패")
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
        """음성 모듈 초기화 (새 파이프라인 사용)"""
        # 마이크
        try:
            from modules.microphone import MicrophoneCapture
            self._microphone = MicrophoneCapture(self.config)
            if self._microphone.open():
                self.state.voice_status = "MIC_READY"
                device = self._microphone.get_device_info()
                if device:
                    self.logger.info(f"[VOICE] MIC_READY device=\"{device.name}\" sr={self.config.audio_sample_rate}")
            else:
                self.state.voice_status = "MIC_ERROR"
                self._microphone = None
        except ImportError:
            self.state.voice_status = "sounddevice 미설치"
            self._microphone = None
        except Exception as e:
            self.state.voice_status = f"MIC_ERROR: {e}"
            self._microphone = None

        # 음성 파이프라인 (VAD + Feature + Classifier 통합)
        try:
            from modules.voice_pipeline import VoicePipeline
            self._voice_pipeline = VoicePipeline(self.config)
            self._voice_pipeline.initialize()
            self.logger.info(f"[VOICE] Pipeline initialized (mode: {self._voice_pipeline.classifier_mode})")
        except ImportError as e:
            self.logger.warning(f"음성 파이프라인 초기화 실패 (의존성): {e}")
            self._voice_pipeline = None
        except Exception as e:
            self.logger.error(f"음성 파이프라인 초기화 실패: {e}")
            self._voice_pipeline = None

        # 분리된 평균 계산기
        try:
            from modules.voice_averager import VoiceAverager
            self._voice_averager = VoiceAverager(self.config)
        except Exception as e:
            self.logger.error(f"VoiceAverager 초기화 실패: {e}")
            from modules.voice_averager import VoiceAverager
            self._voice_averager = VoiceAverager(self.config)

    def _init_lstm(self):
        """LSTM 초기화"""
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
        """TTS 초기화"""
        try:
            from modules.voice_feedback import VoiceFeedback
            self._voice_feedback = VoiceFeedback(self.config)
            self._voice_feedback.initialize()
            if self._voice_feedback.init_error:
                self.logger.warning(self._voice_feedback.init_error)
            if self._microphone and self._voice_feedback:
                self._voice_feedback.set_callbacks(
                    on_start=lambda: self._microphone.set_tts_playing(True),
                    on_end=lambda: self._microphone.set_tts_playing(False),
                )
        except Exception as e:
            self.logger.error(f"TTS 초기화 실패: {e}")
            self._voice_feedback = None

    def _init_stt(self):
        """STT 엔진 초기화 (optional, 실패해도 앱 계속)"""
        try:
            from modules.stt_engine import create_stt_engine, STTHistory
            self._stt_engine = create_stt_engine(self.config)
            self._stt_history = STTHistory(max_size=self.config.stt_history_size)

            if self._stt_engine.is_ready and self.config.stt_enabled:
                self.logger.info(f"[STT] 초기화 완료 (engine: {self._stt_engine.engine_name})")
            elif self._stt_engine.init_error:
                self.logger.warning(f"[STT] {self._stt_engine.init_error}")
        except ImportError:
            self.logger.info("[STT] STT 모듈 미설치 (optional)")
            self._stt_engine = None
            self._stt_history = None
        except Exception as e:
            self.logger.error(f"[STT] 초기화 실패: {e}")
            self._stt_engine = None
            self._stt_history = None

    # ================================================================
    # 시작 / 정지
    # ================================================================

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
        """분석 파이프라인 정지 (idempotent: 여러 번 호출해도 안전)"""
        if not self._running:
            return  # 이미 정지됨 - 중복 호출 방지

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
        """모든 리소스 해제 (idempotent: 여러 번 호출해도 안전)"""
        if self._cleaned_up:
            return  # 이미 cleanup됨 - 중복 호출 방지

        self.stop()
        if self._webcam:
            try:
                self._webcam.release()
            except Exception:
                pass
            self._webcam = None
        if self._microphone:
            try:
                self._microphone.close()
            except Exception:
                pass
            self._microphone = None
        self._cleaned_up = True
        self.logger.info("리소스 해제 완료")

    # ================================================================
    # Hot-update (슬라이더 변경 시 전체 재초기화 없이 반영)
    # ================================================================

    def update_cycle(self, new_cycle: int):
        """분석 주기 변경 (hot-update)"""
        self.config.update_cycle(new_cycle)
        self.state.cycle_seconds = self.config.cycle_seconds
        self._timer.reset(self.config.cycle_seconds)
        if self._microphone:
            try:
                self._microphone.update_cycle(self.config.cycle_seconds)
            except Exception:
                pass
        if self._voice_averager:
            self._voice_averager.reset()
        if self._lstm_predictor:
            self._lstm_predictor.reset()
        self._smoother.reset()
        self.state.add_log(f"주기 변경: {self.config.cycle_seconds}초")
        self._notify_state()

    def update_volume(self, new_volume: int):
        """볼륨 변경 (hot-update)"""
        self.config.update_volume(new_volume)
        self.state.volume = self.config.tts_volume
        if self._voice_feedback:
            self._voice_feedback.set_volume(self.config.tts_volume)

    def update_voice_feedback(self, enabled: bool):
        """TTS ON/OFF (hot-update)"""
        self.config.tts_enabled = enabled
        self.state.voice_feedback_enabled = enabled
        if self._voice_feedback:
            self._voice_feedback.set_enabled(enabled)

    def update_camera_index(self, new_index: int):
        """카메라 인덱스 변경 (재초기화 필요)"""
        was_running = self._running
        if was_running:
            self.stop()
        self.config.camera_device_id = new_index
        if self._webcam:
            try:
                self._webcam.release()
            except Exception:
                pass
            self._webcam = None
        self._init_camera()
        if was_running:
            self.start()
        self._notify_state()

    def update_smoothing(self, window_size: int, threshold: float):
        """결과 안정화 파라미터 변경 (hot-update)"""
        self._smoother.update_window_size(window_size)
        self._smoother.update_threshold(threshold)
        self.config.smoothing_window = window_size
        self.config.confidence_threshold = threshold

    # ================================================================
    # 분석 루프
    # ================================================================

    def _face_analysis_loop(self):
        """표정 분석 루프 (별도 스레드) - 상세 debug 로그 포함"""
        retry_count = 0
        cpu_saver_sleep = 0.05 if self.config.cpu_saver else 0.02
        analysis_count = 0

        self.logger.info("[LOOP] 표정 분석 루프 시작")
        self.state.add_log("🔄 분석 루프 시작됨")

        while self._running and self.state.camera_active:
            try:
                success, frame = self._webcam.read_frame()
                if not success:
                    retry_count += 1
                    if retry_count >= self.config.camera_retry_count:
                        self.state.face_status = "NO_FRAME"
                        self.state.add_log("⚠️ 프레임 읽기 실패 (NO_FRAME)")
                        time.sleep(1.0)
                        retry_count = 0
                    time.sleep(0.1)
                    continue

                retry_count = 0
                self._frame_count += 1

                # 라이브 프리뷰용 프레임 저장 (매 프레임)
                if self.config.live_preview_enabled:
                    self.state.latest_frame = frame

                # 프레임 스킵
                if self._frame_count % self.config.analysis_skip_frames != 0:
                    time.sleep(cpu_saver_sleep)
                    continue

                # 얼굴 감지
                faces = self._webcam.detect_faces(frame)
                if not faces:
                    self.state.face_status = "NO_FACE"
                    # 주기적으로 로그 출력 (매번은 너무 많음)
                    if self._frame_count % (self.config.analysis_skip_frames * 10) == 0:
                        self.state.add_log("👤 얼굴 미감지 (NO_FACE)")
                    time.sleep(cpu_saver_sleep)
                    continue

                self.state.face_status = "분석 중"
                largest = self._webcam.get_largest_face(faces)
                face_img = self._webcam.crop_face(frame, largest)
                if face_img is None:
                    self.state.face_status = "CROP_FAILED"
                    continue

                # 표정 분류
                face_result = None
                if self._face_classifier:
                    face_result = self._face_classifier.classify(face_img)

                if face_result is None:
                    self.state.face_status = "DEEPFACE_ERROR"
                    self.state.add_log("⚠️ 분류 실패 (DEEPFACE_ERROR)")
                    continue

                analysis_count += 1

                # 결과 처리 (smoothing 적용)
                with self._lock:
                    self._smoother.add(face_result)
                    smoothed = self._smoother.get_smoothed()

                    # ★ smoothed가 None이어도 raw result는 표시
                    display_result = smoothed if smoothed else face_result
                    self.state.current_emotion = display_result
                    self.state.face_status = f"분석 중 ({display_result.dominant} {display_result.confidence:.0%})"

                    # face 결과를 voice_averager에 추가 (분리 평균 계산용)
                    if self._voice_averager:
                        self._voice_averager.add_face_result(display_result)

                    # 첫 결과 및 주기적 debug 로그
                    if analysis_count == 1 or analysis_count % 5 == 0:
                        self.state.add_log(
                            f"📊 분석 #{analysis_count}: {display_result.dominant} "
                            f"({display_result.confidence:.0%}) [{display_result.source}]"
                        )

                self._notify_state()
                time.sleep(cpu_saver_sleep)

            except Exception as e:
                self.logger.error(f"표정 분석 루프 오류: {e}")
                self.state.face_status = f"오류: {e}"
                self.state.add_log(f"❌ 루프 오류: {e}")
                time.sleep(0.5)

        self.logger.info(f"[LOOP] 표정 분석 루프 종료 (분석 횟수: {analysis_count})")
        self.state.add_log(f"🛑 분석 루프 종료 (총 {analysis_count}회 분석)")

    def _on_cycle_complete(self):
        """주기 완료 콜백"""
        try:
            with self._lock:
                self._process_cycle_end()
        except Exception as e:
            self.logger.error(f"주기 처리 오류: {e}")

    def _process_cycle_end(self):
        """
        주기 종료 처리 (새 음성 파이프라인 통합).
        face/voice 결과를 분리 평균하고, 동적 가중치로 통합합니다.
        """
        # ① 음성 파이프라인 실행 (voice/full 모드)
        if self.config.use_voice and self._microphone and self._voice_pipeline:
            try:
                audio = self._microphone.get_buffer()
                voice_result = self._voice_pipeline.process(audio, self.config.audio_sample_rate)

                # 파이프라인 상태를 state에 저장 (UI 표시용)
                self.state.voice_pipeline_state = self._voice_pipeline.state

                if voice_result.status in ("EMOTION_CLASSIFIED", "LOW_CONFIDENCE"):
                    if voice_result.emotion:
                        self._voice_averager.add_voice_result(voice_result)
                        self.state.voice_status = f"분석: {voice_result.emotion.dominant} ({voice_result.confidence_tier})"
                elif voice_result.status == "SILENCE_DETECTED":
                    self.state.voice_status = "무음"
                elif voice_result.status == "INSUFFICIENT_VOICE_DATA":
                    self.state.voice_status = "발화 부족"
                else:
                    self.state.voice_status = f"상태: {voice_result.status}"

                # 파이프라인 로그를 app 로그에 추가
                for msg in self._voice_pipeline.state.log_messages:
                    self.state.add_log(msg)

                # ① -b. STT 실행 (VAD가 유효 발화일 때만)
                if (self.config.stt_enabled and self._stt_engine and
                        self._stt_engine.is_ready and
                        voice_result.status in ("EMOTION_CLASSIFIED", "LOW_CONFIDENCE")):
                    try:
                        # VAD 유효 발화 시간이 STT 최소 기준 충족하는지 확인
                        vad = getattr(self._voice_pipeline.state, 'vad_result', None)
                        valid_sec = vad.valid_seconds if vad else 0.0

                        if valid_sec >= self.config.stt_min_speech_seconds:
                            stt_result = self._stt_engine.transcribe(audio, self.config.audio_sample_rate)
                            self.state.stt_latest = stt_result
                            self.state.add_log(stt_result.to_log_string())

                            if self._stt_history:
                                self._stt_history.add(stt_result)
                                self.state.stt_history = self._stt_history.get_recent()
                        else:
                            from modules.stt_engine import STTResult, STT_SILENCE
                            self.state.stt_latest = STTResult(
                                status=STT_SILENCE,
                                error_message=f"발화 {valid_sec:.1f}s < 최소 {self.config.stt_min_speech_seconds}s"
                            )
                    except Exception as e:
                        self.logger.error(f"[STT] 실행 실패: {e}")

            except Exception as e:
                self.logger.error(f"음성 파이프라인 실패: {e}")
                self.state.voice_status = f"오류: {e}"

        # ② 분리된 평균 계산 (face + voice → integrated → final)
        averages = self._voice_averager.calculate_averages()

        final_avg = averages.final_average
        if final_avg:
            self.state.average_emotion = final_avg
            self.state.add_log(
                f"[FUSION] face={'✓' if averages.face_average else '✗'} "
                f"voice={'✓' if averages.voice_average else '✗'} "
                f"face_w={averages.applied_face_weight:.2f} "
                f"voice_w={averages.applied_voice_weight:.2f} "
                f"final={final_avg.dominant}"
            )
            self.logger.emotion("average", {
                "dominant": final_avg.dominant,
                "confidence": final_avg.confidence,
                "scores": final_avg.scores,
            })

            # ③ LSTM 예측
            if self._lstm_predictor:
                try:
                    self._lstm_predictor.add_data_point(final_avg.scores)
                    if self._lstm_predictor.is_ready:
                        predicted = self._lstm_predictor.predict()
                        if predicted:
                            self.state.predicted_emotion = predicted
                            self.state.lstm_status = f"예측 중 ({self._lstm_predictor.mode_name})"
                            self.state.add_log(f"예측: {predicted.dominant} ({predicted.confidence:.0%})")

                            # ④ 비교
                            if self._comparator:
                                label, magnitude = self._comparator.compare(final_avg.scores, predicted.scores)
                                self.state.comparison_label = label
                                self.state.comparison_magnitude = magnitude
                                self.state.add_log(f"비교: {label} ({magnitude:.2f})")
                    else:
                        self.state.lstm_status = f"수집 중 ({self._lstm_predictor.data_count}/{self.config.lstm_min_data_points})"
                except Exception as e:
                    self.logger.error(f"LSTM 예측 실패: {e}")
                    self.state.lstm_status = "예측 오류"

            # ⑤ 음성 안내
            if self._voice_feedback and self.config.tts_enabled:
                try:
                    message = self._voice_feedback.speak(
                        final_avg.dominant, self.state.comparison_label
                    )
                    if message:
                        self.state.add_log(f"TTS: {message}")
                except Exception as e:
                    self.logger.error(f"TTS 실패: {e}")
        else:
            self.state.add_log("데이터 부족")

        # 주기 리셋
        self._voice_averager.reset()
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
