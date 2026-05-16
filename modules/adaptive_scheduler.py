"""
modules/adaptive_scheduler.py - 적응형 스케줄러
분석 모듈의 실행 주기를 상태에 따라 동적으로 조절합니다.

상태 코드:
- FAST_TRACKING: 표정 변화가 클 때 (빠른 분석)
- NORMAL_TRACKING: 일반 상태
- LOW_ACTIVITY: 표정 변화 적음 (느린 분석)
- NO_FACE_SLOWDOWN: 얼굴 미감지 시 interval 증가
- CPU_THROTTLE: CPU 부하 높을 때 자동 throttle

핵심 동작:
- 얼굴 미감지 시 interval 점진 증가, 감지 시 빠르게 감소
- 표정 변화량(delta)에 따라 LSTM update 주기 조정
- CPU 부하 감지 시 모든 주기를 자동으로 늘림
"""

import time
import os
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum


class SchedulerState(str, Enum):
    """스케줄러 상태 코드"""
    FAST_TRACKING = "FAST_TRACKING"
    NORMAL_TRACKING = "NORMAL_TRACKING"
    LOW_ACTIVITY = "LOW_ACTIVITY"
    NO_FACE_SLOWDOWN = "NO_FACE_SLOWDOWN"
    CPU_THROTTLE = "CPU_THROTTLE"


@dataclass
class IntervalSet:
    """현재 적용 중인 분석 주기 세트"""
    face_detection_sec: float = 1.0
    face_emotion_sec: float = 2.0
    lstm_update_sec: float = 1.0
    voice_analysis_sec: float = 5.0
    ui_refresh_sec: float = 0.7


@dataclass
class SchedulerStatus:
    """스케줄러 현재 상태 정보 (외부 조회용)"""
    state: SchedulerState = SchedulerState.NORMAL_TRACKING
    intervals: IntervalSet = field(default_factory=IntervalSet)
    no_face_streak: int = 0
    cpu_usage: float = 0.0
    expression_delta: float = 0.0
    last_update_time: float = field(default_factory=time.time)


class AdaptiveScheduler:
    """
    적응형 스케줄러.
    얼굴 감지 상태, 표정 변화량, CPU 부하에 따라 분석 주기를 동적 조절합니다.
    """

    # 얼굴 미감지 시 interval 배수 증가 설정
    NO_FACE_SLOWDOWN_FACTOR = 1.5       # 미감지마다 이 배수만큼 증가
    NO_FACE_MAX_MULTIPLIER = 4.0        # 최대 배수 제한
    NO_FACE_STREAK_THRESHOLD = 3        # 연속 N회 미감지 후 slowdown 시작

    # 표정 변화량 임계값
    EXPRESSION_DELTA_HIGH = 0.3         # 이상이면 FAST_TRACKING
    EXPRESSION_DELTA_LOW = 0.05         # 이하이면 LOW_ACTIVITY

    # CPU throttle 임계값
    CPU_THROTTLE_THRESHOLD = 80.0       # CPU 사용률 80% 이상이면 throttle
    CPU_THROTTLE_MULTIPLIER = 2.0       # throttle 시 interval 배수

    # 감지 복귀 시 빠른 감소 비율
    FACE_RECOVERY_FACTOR = 0.5          # 감지 복귀 시 즉시 interval 절반으로

    def __init__(self, config):
        """
        Args:
            config: Config 인스턴스 (base interval 값 참조)
        """
        self._config = config
        self._lock = threading.Lock()

        # 기본(base) interval (config에서 가져옴)
        self._base_intervals = IntervalSet(
            face_detection_sec=config.face_detection_interval_sec,
            face_emotion_sec=config.face_emotion_interval_sec,
            lstm_update_sec=config.lstm_update_interval_sec,
            voice_analysis_sec=config.voice_analysis_interval_sec,
            ui_refresh_sec=config.ui_refresh_interval_sec,
        )

        # 현재 적용 중인 interval (동적 조절됨)
        self._current_intervals = IntervalSet(
            face_detection_sec=self._base_intervals.face_detection_sec,
            face_emotion_sec=self._base_intervals.face_emotion_sec,
            lstm_update_sec=self._base_intervals.lstm_update_sec,
            voice_analysis_sec=self._base_intervals.voice_analysis_sec,
            ui_refresh_sec=self._base_intervals.ui_refresh_sec,
        )

        # 상태 추적
        self._state = SchedulerState.NORMAL_TRACKING
        self._no_face_streak = 0
        self._expression_delta = 0.0
        self._cpu_usage = 0.0
        self._last_cpu_check = 0.0
        self._cpu_check_interval = 2.0  # CPU 체크 주기 (초)

        # 이전 감정 스코어 (변화량 계산용)
        self._prev_scores: Optional[Dict[str, float]] = None

    @property
    def state(self) -> SchedulerState:
        """현재 스케줄러 상태"""
        with self._lock:
            return self._state

    @property
    def intervals(self) -> IntervalSet:
        """현재 적용 중인 interval 세트"""
        with self._lock:
            return IntervalSet(
                face_detection_sec=self._current_intervals.face_detection_sec,
                face_emotion_sec=self._current_intervals.face_emotion_sec,
                lstm_update_sec=self._current_intervals.lstm_update_sec,
                voice_analysis_sec=self._current_intervals.voice_analysis_sec,
                ui_refresh_sec=self._current_intervals.ui_refresh_sec,
            )

    def get_status(self) -> SchedulerStatus:
        """스케줄러 전체 상태 조회"""
        with self._lock:
            return SchedulerStatus(
                state=self._state,
                intervals=IntervalSet(
                    face_detection_sec=self._current_intervals.face_detection_sec,
                    face_emotion_sec=self._current_intervals.face_emotion_sec,
                    lstm_update_sec=self._current_intervals.lstm_update_sec,
                    voice_analysis_sec=self._current_intervals.voice_analysis_sec,
                    ui_refresh_sec=self._current_intervals.ui_refresh_sec,
                ),
                no_face_streak=self._no_face_streak,
                cpu_usage=self._cpu_usage,
                expression_delta=self._expression_delta,
                last_update_time=time.time(),
            )

    # ================================================================
    # 이벤트 수신 (controller에서 호출)
    # ================================================================

    def on_face_detected(self, emotion_scores: Optional[Dict[str, float]] = None):
        """
        얼굴 감지됨 이벤트.
        interval을 빠르게 복귀시키고, 표정 변화량을 계산합니다.

        Args:
            emotion_scores: 현재 감정 스코어 딕셔너리 (예: {"happy": 0.8, "sad": 0.1, ...})
        """
        with self._lock:
            # 얼굴 감지 복귀 - streak 리셋, interval 빠르게 감소
            if self._no_face_streak > 0:
                self._no_face_streak = 0
                self._recover_intervals()

            # 표정 변화량 계산
            if emotion_scores and self._prev_scores:
                self._expression_delta = self._calculate_delta(
                    self._prev_scores, emotion_scores
                )
            elif emotion_scores:
                self._expression_delta = 0.0

            if emotion_scores:
                self._prev_scores = dict(emotion_scores)

            # 상태 결정 (CPU throttle이 최우선)
            self._update_state()
            self._apply_state_intervals()

    def on_no_face_detected(self):
        """
        얼굴 미감지 이벤트.
        연속 미감지 횟수를 증가시키고, 임계값 초과 시 interval을 늘립니다.
        """
        with self._lock:
            self._no_face_streak += 1
            self._expression_delta = 0.0

            # 상태 결정
            self._update_state()
            self._apply_state_intervals()

    def on_tick(self):
        """
        주기적 틱 (매 분석 루프 반복마다 호출).
        CPU 부하를 주기적으로 체크합니다.
        """
        now = time.time()
        if now - self._last_cpu_check >= self._cpu_check_interval:
            self._last_cpu_check = now
            self._check_cpu_usage()

            with self._lock:
                self._update_state()
                self._apply_state_intervals()

    def reset(self):
        """스케줄러 상태 초기화 (프로파일 변경 시 호출)"""
        with self._lock:
            self._base_intervals = IntervalSet(
                face_detection_sec=self._config.face_detection_interval_sec,
                face_emotion_sec=self._config.face_emotion_interval_sec,
                lstm_update_sec=self._config.lstm_update_interval_sec,
                voice_analysis_sec=self._config.voice_analysis_interval_sec,
                ui_refresh_sec=self._config.ui_refresh_interval_sec,
            )
            self._current_intervals = IntervalSet(
                face_detection_sec=self._base_intervals.face_detection_sec,
                face_emotion_sec=self._base_intervals.face_emotion_sec,
                lstm_update_sec=self._base_intervals.lstm_update_sec,
                voice_analysis_sec=self._base_intervals.voice_analysis_sec,
                ui_refresh_sec=self._base_intervals.ui_refresh_sec,
            )
            self._state = SchedulerState.NORMAL_TRACKING
            self._no_face_streak = 0
            self._expression_delta = 0.0
            self._prev_scores = None

    # ================================================================
    # 내부 로직
    # ================================================================

    def _update_state(self):
        """현재 조건에 따라 스케줄러 상태 결정 (우선순위 순)"""
        # 1) CPU throttle (최우선)
        if self._cpu_usage >= self.CPU_THROTTLE_THRESHOLD:
            self._state = SchedulerState.CPU_THROTTLE
            return

        # 2) 얼굴 미감지 slowdown
        if self._no_face_streak >= self.NO_FACE_STREAK_THRESHOLD:
            self._state = SchedulerState.NO_FACE_SLOWDOWN
            return

        # 3) 표정 변화량 기반
        if self._expression_delta >= self.EXPRESSION_DELTA_HIGH:
            self._state = SchedulerState.FAST_TRACKING
        elif self._expression_delta <= self.EXPRESSION_DELTA_LOW:
            self._state = SchedulerState.LOW_ACTIVITY
        else:
            self._state = SchedulerState.NORMAL_TRACKING

    def _apply_state_intervals(self):
        """현재 상태에 따라 interval 값 조절"""
        base = self._base_intervals

        if self._state == SchedulerState.CPU_THROTTLE:
            mult = self.CPU_THROTTLE_MULTIPLIER
            self._current_intervals.face_detection_sec = base.face_detection_sec * mult
            self._current_intervals.face_emotion_sec = base.face_emotion_sec * mult
            self._current_intervals.lstm_update_sec = base.lstm_update_sec * mult
            self._current_intervals.voice_analysis_sec = base.voice_analysis_sec * mult
            self._current_intervals.ui_refresh_sec = base.ui_refresh_sec * mult

        elif self._state == SchedulerState.NO_FACE_SLOWDOWN:
            # 미감지 streak에 비례하여 증가 (상한 있음)
            streak_over = self._no_face_streak - self.NO_FACE_STREAK_THRESHOLD + 1
            mult = min(
                self.NO_FACE_SLOWDOWN_FACTOR ** streak_over,
                self.NO_FACE_MAX_MULTIPLIER,
            )
            self._current_intervals.face_detection_sec = base.face_detection_sec * mult
            self._current_intervals.face_emotion_sec = base.face_emotion_sec * mult
            # LSTM과 voice는 느리게 증가
            self._current_intervals.lstm_update_sec = base.lstm_update_sec * min(mult, 2.0)
            self._current_intervals.voice_analysis_sec = base.voice_analysis_sec
            self._current_intervals.ui_refresh_sec = base.ui_refresh_sec * min(mult, 1.5)

        elif self._state == SchedulerState.FAST_TRACKING:
            # 변화가 클 때 - interval 감소 (빠르게 분석)
            fast_mult = 0.5
            self._current_intervals.face_detection_sec = base.face_detection_sec * fast_mult
            self._current_intervals.face_emotion_sec = base.face_emotion_sec * fast_mult
            self._current_intervals.lstm_update_sec = base.lstm_update_sec * fast_mult
            self._current_intervals.voice_analysis_sec = base.voice_analysis_sec
            self._current_intervals.ui_refresh_sec = base.ui_refresh_sec * 0.7

        elif self._state == SchedulerState.LOW_ACTIVITY:
            # 변화가 적을 때 - interval 약간 증가
            slow_mult = 1.5
            self._current_intervals.face_detection_sec = base.face_detection_sec * slow_mult
            self._current_intervals.face_emotion_sec = base.face_emotion_sec * slow_mult
            self._current_intervals.lstm_update_sec = base.lstm_update_sec * slow_mult
            self._current_intervals.voice_analysis_sec = base.voice_analysis_sec
            self._current_intervals.ui_refresh_sec = base.ui_refresh_sec

        else:
            # NORMAL_TRACKING - base 값 그대로
            self._current_intervals.face_detection_sec = base.face_detection_sec
            self._current_intervals.face_emotion_sec = base.face_emotion_sec
            self._current_intervals.lstm_update_sec = base.lstm_update_sec
            self._current_intervals.voice_analysis_sec = base.voice_analysis_sec
            self._current_intervals.ui_refresh_sec = base.ui_refresh_sec

    def _recover_intervals(self):
        """얼굴 감지 복귀 시 interval을 빠르게 base 값으로 되돌림"""
        base = self._base_intervals
        factor = self.FACE_RECOVERY_FACTOR

        # 현재 값과 base 사이를 빠르게 보간
        self._current_intervals.face_detection_sec = max(
            base.face_detection_sec,
            self._current_intervals.face_detection_sec * factor,
        )
        self._current_intervals.face_emotion_sec = max(
            base.face_emotion_sec,
            self._current_intervals.face_emotion_sec * factor,
        )
        self._current_intervals.lstm_update_sec = max(
            base.lstm_update_sec,
            self._current_intervals.lstm_update_sec * factor,
        )
        self._current_intervals.ui_refresh_sec = max(
            base.ui_refresh_sec,
            self._current_intervals.ui_refresh_sec * factor,
        )

    def _calculate_delta(self, prev: Dict[str, float], curr: Dict[str, float]) -> float:
        """
        두 감정 스코어 간 변화량 계산 (L1 distance / 2).
        결과 범위: 0.0 ~ 1.0
        """
        total = 0.0
        keys = set(prev.keys()) | set(curr.keys())
        for k in keys:
            total += abs(prev.get(k, 0.0) - curr.get(k, 0.0))
        # 정규화 (최대 변화량 = 2.0일 때 delta = 1.0)
        return min(total / 2.0, 1.0)

    def _check_cpu_usage(self):
        """시스템 CPU 사용률 체크 (cross-platform)"""
        try:
            # psutil 사용 시도
            import psutil
            self._cpu_usage = psutil.cpu_percent(interval=0)
        except ImportError:
            # psutil 없을 때 /proc/stat 파싱 (Linux)
            try:
                self._cpu_usage = self._read_proc_cpu()
            except Exception:
                # 측정 불가 시 0으로 (throttle 비활성화)
                self._cpu_usage = 0.0

    def _read_proc_cpu(self) -> float:
        """Linux /proc/stat에서 CPU 사용률 계산"""
        if not os.path.exists("/proc/stat"):
            return 0.0

        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            parts = line.split()
            # cpu user nice system idle iowait irq softirq steal
            if len(parts) < 5:
                return 0.0

            idle = int(parts[4])
            total = sum(int(x) for x in parts[1:])

            if not hasattr(self, "_prev_cpu_idle"):
                self._prev_cpu_idle = idle
                self._prev_cpu_total = total
                return 0.0

            idle_delta = idle - self._prev_cpu_idle
            total_delta = total - self._prev_cpu_total
            self._prev_cpu_idle = idle
            self._prev_cpu_total = total

            if total_delta == 0:
                return 0.0

            usage = (1.0 - idle_delta / total_delta) * 100.0
            return max(0.0, min(100.0, usage))
        except Exception:
            return 0.0
