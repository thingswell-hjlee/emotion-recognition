"""
utils/logger.py - 로그 관리 모듈
콘솔 출력 + 파일 저장 (logs/app.log)
⚠️ 얼굴 이미지, 원본 음성은 절대 저장하지 않습니다.
저장: 시간, 모듈명, 이벤트 유형, 감정 점수만
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any


class Logger:
    """감정 분석 로그 관리 (콘솔 + 파일)"""

    def __init__(self, log_file: Optional[str] = "logs/app.log", console: bool = True):
        self.log_file = log_file
        self.console = console
        self._logger = None

        # 로그 디렉토리 생성
        if self.log_file:
            try:
                os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            except Exception:
                self.log_file = None

        # Python logging 설정
        self._setup_logging()

    def _setup_logging(self):
        """표준 logging 모듈 설정"""
        self._logger = logging.getLogger("emotion_monitor")
        self._logger.setLevel(logging.DEBUG)

        # 기존 핸들러 제거
        self._logger.handlers.clear()

        # 콘솔 핸들러
        if self.console:
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)
            fmt = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s',
                                    datefmt='%H:%M:%S')
            ch.setFormatter(fmt)
            self._logger.addHandler(ch)

        # 파일 핸들러
        if self.log_file:
            try:
                fh = logging.FileHandler(self.log_file, encoding='utf-8')
                fh.setLevel(logging.DEBUG)
                fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
                fh.setFormatter(fmt)
                self._logger.addHandler(fh)
            except Exception:
                pass

    def info(self, message: str):
        """정보 로그"""
        try:
            self._logger.info(message)
        except Exception:
            pass

    def warning(self, message: str):
        """경고 로그"""
        try:
            self._logger.warning(message)
        except Exception:
            pass

    def error(self, message: str):
        """에러 로그"""
        try:
            self._logger.error(message)
        except Exception:
            pass

    def debug(self, message: str):
        """디버그 로그"""
        try:
            self._logger.debug(message)
        except Exception:
            pass

    def emotion(self, event_type: str, data: Dict[str, Any]):
        """
        감정 분석 결과 로그.
        ⚠️ 이미지/음성 데이터는 포함하지 않음.
        저장: 시간, 모듈명, 감정 점수만.
        """
        try:
            timestamp = datetime.now().isoformat()
            dominant = data.get("dominant", "")
            confidence = data.get("confidence", 0)

            # 콘솔 출력
            self._logger.info(f"{event_type}: {dominant} ({confidence:.0%})")

            # JSONL 파일 저장 (점수 데이터만)
            if self.log_file:
                entry = {
                    "timestamp": timestamp,
                    "type": event_type,
                    "dominant": dominant,
                    "confidence": round(confidence, 3),
                }
                # scores 딕셔너리가 있으면 포함 (숫자만)
                if "scores" in data:
                    entry["scores"] = {k: round(v, 3) for k, v in data["scores"].items()}
                self._write_jsonl(entry)
        except Exception:
            pass

    def _write_jsonl(self, entry: Dict):
        """JSON Lines 형식으로 파일에 추가"""
        try:
            jsonl_path = self.log_file.replace('.log', '.jsonl') if self.log_file else None
            if jsonl_path:
                with open(jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass
