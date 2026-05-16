"""
utils/timer.py - 주기 타이머 모듈
분석 주기를 관리하고 주기 종료 시 콜백을 실행합니다.
"""

import time
import threading
from typing import Callable, Optional


class CycleTimer:
    """분석 주기 타이머"""

    def __init__(self, cycle_seconds: int = 10,
                 on_cycle_complete: Optional[Callable] = None):
        """
        Args:
            cycle_seconds: 주기 길이 (초)
            on_cycle_complete: 주기 종료 시 호출할 콜백 함수
        """
        self.cycle_seconds = cycle_seconds
        self.on_cycle_complete = on_cycle_complete
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._start_time: float = 0.0
        self._cycle_count: int = 0

    def start(self):
        """타이머 시작"""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._cycle_count = 0
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """타이머 정지"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def reset(self, new_cycle_seconds: Optional[int] = None):
        """타이머 리셋 (주기 변경 시)"""
        was_running = self._running
        self.stop()
        if new_cycle_seconds is not None:
            self.cycle_seconds = new_cycle_seconds
        if was_running:
            self.start()

    @property
    def elapsed(self) -> float:
        """현재 주기 내 경과 시간 (초)"""
        if not self._running:
            return 0.0
        return time.time() - self._start_time

    @property
    def remaining(self) -> float:
        """현재 주기 내 남은 시간 (초)"""
        return max(0.0, self.cycle_seconds - (self.elapsed % self.cycle_seconds))

    @property
    def cycle_count(self) -> int:
        """완료된 주기 수"""
        return self._cycle_count

    @property
    def is_running(self) -> bool:
        return self._running

    def _run(self):
        """타이머 루프 (별도 스레드)"""
        while self._running:
            time.sleep(0.1)  # 100ms 간격으로 체크
            elapsed = time.time() - self._start_time
            current_cycle = int(elapsed / self.cycle_seconds)

            if current_cycle > self._cycle_count:
                self._cycle_count = current_cycle
                if self.on_cycle_complete:
                    try:
                        self.on_cycle_complete()
                    except Exception as e:
                        print(f"[ERROR] 주기 콜백 실행 실패: {e}")
