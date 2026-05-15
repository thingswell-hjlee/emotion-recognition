"""
utils/logger.py - 로그 관리 모듈
콘솔 출력과 파일 저장을 담당합니다.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any


class Logger:
    """감정 분석 로그 관리"""

    def __init__(self, log_file: Optional[str] = None, console: bool = True):
        """
        Args:
            log_file: 로그 파일 경로 (None이면 파일 저장 안함)
            console: 콘솔 출력 여부
        """
        self.log_file = log_file
        self.console = console

        # 로그 디렉토리 생성
        if self.log_file:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def info(self, message: str):
        """정보 로그"""
        self._log("INFO", message)

    def warning(self, message: str):
        """경고 로그"""
        self._log("WARNING", message)

    def error(self, message: str):
        """에러 로그"""
        self._log("ERROR", message)

    def emotion(self, event_type: str, data: Dict[str, Any]):
        """감정 분석 결과 로그 (JSON Lines 형식으로 파일 저장)"""
        timestamp = datetime.now().isoformat()
        entry = {
            "timestamp": timestamp,
            "type": event_type,
            **data,
        }

        if self.console:
            dominant = data.get("dominant", "")
            confidence = data.get("confidence", 0)
            print(f"[{timestamp[:19]}] {event_type}: {dominant} ({confidence:.0%})")

        if self.log_file:
            self._write_jsonl(entry)

    def _log(self, level: str, message: str):
        """내부 로그 출력"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{level}] [{timestamp}] {message}"

        if self.console:
            print(formatted)

    def _write_jsonl(self, entry: Dict):
        """JSON Lines 형식으로 파일에 추가"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except IOError as e:
            if self.console:
                print(f"[ERROR] 로그 파일 쓰기 실패: {e}")
