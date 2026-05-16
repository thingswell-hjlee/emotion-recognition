# -*- coding: utf-8 -*-
"""
Thingswell Inc. - Version and Product Information
Central source of truth for all company/product metadata.
All UI, documents, logs, and release scripts should reference this file.
"""

from datetime import datetime

APP_NAME = "Multimodal Emotion Recognition & Korean STT Monitor"
PROJECT_NAME = "emotion-recognition"
COMPANY_NAME = "Thingswell Inc."
VERSION = "0.1.0"
RELEASE_CHANNEL = "Beta Test Release"
BUILD_TAG = f"beta-win64-v{VERSION}"
COPYRIGHT = "Copyright © 2026 Thingswell Inc. All rights reserved."
AUTHOR = "Thingswell Inc. AI Solution Development Team"
CONTACT_EMAIL = "hjlee@thingswell.co.kr"
WEBSITE = "https://thingswell.co.kr"
BUILD_DATE = datetime.now().strftime("%Y-%m-%d")

LICENSE_NOTICE_EN = (
    "This software is provided for internal testing, research, demonstration, "
    "and reliability/performance evaluation purposes only. "
    "Unauthorized copying, redistribution, reverse engineering, commercial resale, "
    "or public deployment is prohibited without written permission from Thingswell Inc."
)

LICENSE_NOTICE_KO = (
    "본 소프트웨어는 Thingswell Inc.의 내부 연구, 기능 검증, 신뢰성 시험, "
    "성능 평가 및 데모 목적으로 제공됩니다. "
    "Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, "
    "상업적 재판매, 외부 공개 배포를 금지합니다."
)

PRIVACY_NOTICE_EN = (
    "This application uses a camera and microphone. "
    "Please obtain user consent before testing. "
    "Generated logs may include device information, performance metrics, and analysis results. "
    "By default, raw face/audio data should not be stored. "
    "If raw data recording is added, explicit consent is required."
)

PRIVACY_NOTICE_KO = (
    "이 앱은 카메라와 마이크를 사용합니다. "
    "테스트 전 사용자 동의를 받고 진행하세요. "
    "테스트 중 생성되는 로그에는 장치 정보, 성능 정보, 분석 결과가 포함될 수 있습니다. "
    "민감한 얼굴/음성 원본 데이터는 저장하지 않는 것을 기본 정책으로 하며, "
    "저장 기능을 추가할 경우 별도 동의가 필요합니다."
)
