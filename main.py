"""
main.py - Multimodal Emotion State Monitor
노트북의 웹캠과 마이크를 사용하여 감정 상태를 인식하고,
주기적 평균 계산, LSTM 예측, 음성 안내를 제공합니다.

사용법:
    streamlit run ui/app.py        # UI 모드 (권장)
    python main.py                  # CLI 모드
    python main.py --no-ui          # UI 없이 CLI만

종료:
    Ctrl+C 또는 UI에서 정지 버튼
"""

import sys
import signal
import argparse
import time
from datetime import datetime
from typing import Optional

# 프로젝트 모듈 (구현 시 import)
# from config import Config
# from controller import EmotionController
# from utils.logger import Logger


def parse_args():
    """CLI 인자 파싱"""
    parser = argparse.ArgumentParser(
        description="Multimodal Emotion State Monitor"
    )
    parser.add_argument(
        "--no-ui", action="store_true",
        help="UI 없이 CLI 모드로 실행"
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="설정 파일 경로 (JSON)"
    )
    parser.add_argument(
        "--cycle", type=int, default=10,
        help="감정 인식 주기 (초, 5~20)"
    )
    parser.add_argument(
        "--mode", type=str, default="integrated",
        choices=["face_only", "voice_only", "integrated"],
        help="분석 모드"
    )
    return parser.parse_args()


def signal_handler(signum, frame):
    """Ctrl+C 시그널 핸들링"""
    print("\n[INFO] 종료 신호를 받았습니다. 프로그램을 종료합니다...")
    sys.exit(0)


def run_cli_mode(args):
    """CLI 모드 실행 (UI 없이)"""
    print("=" * 60)
    print("  Multimodal Emotion State Monitor (CLI Mode)")
    print("=" * 60)
    print()
    print(f"  분석 모드: {args.mode}")
    print(f"  분석 주기: {args.cycle}초")
    print(f"  종료: Ctrl+C")
    print()
    print("  ⚠️  감정 분석 결과는 참고용이며,")
    print("      의학적·심리학적 진단이 아닙니다.")
    print()
    print("=" * 60)
    print()

    from config import Config
    from controller import EmotionController

    config = Config()
    config.cycle_seconds = max(5, min(20, args.cycle))
    config.analysis_mode = args.mode

    controller = EmotionController(config)
    if not controller.initialize():
        print("[ERROR] 초기화 실패. 사용 가능한 장치를 확인하세요.")
        sys.exit(1)

    controller.start()

    try:
        while controller.state.is_running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        controller.cleanup()
        print("\n[INFO] 프로그램을 종료합니다.")


def main():
    """메인 엔트리포인트"""
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # CLI 인자 파싱
    args = parse_args()

    # 실행 모드 결정
    if args.no_ui:
        run_cli_mode(args)
    else:
        print("[INFO] UI 모드로 실행합니다.")
        print("[INFO] 다음 명령어를 사용하세요:")
        print()
        print("    streamlit run ui/app.py")
        print()
        print("[INFO] 또는 --no-ui 옵션으로 CLI 모드를 사용하세요:")
        print()
        print("    python main.py --no-ui")
        print()


if __name__ == "__main__":
    main()
