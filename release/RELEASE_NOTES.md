# Emotion Recognition Beta Windows v0.1.0 - Thingswell Inc.

**Tag:** `beta-win64-v0.1.0`  
**Asset:** `emotion-recognition-beta-win64-v0.1.0-thingswell.zip`  

Produced by Thingswell Inc. AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr  
Website: https://thingswell.co.kr  

---

## Purpose

This release is for internal testing, functional verification, reliability testing, performance evaluation, and demonstration.

---

## Download

Download the ZIP asset from the **Assets** section below:

> **`emotion-recognition-beta-win64-v0.1.0-thingswell.zip`**

After downloading, extract to a simple path (recommended: `C:\thingswell_test\`).

---

## Included Features

- Live camera preview with face detection
- Face emotion analysis (7 emotions: Happy, Sad, Angry, Surprise, Fear, Disgust, Neutral)
- Voice activity detection (VAD) with adaptive noise floor
- Korean STT (Speech-to-Text) using faster-whisper
- Voice emotion baseline analysis (heuristic)
- Performance profiles (Low Power, Standard, High Accuracy, Debug)
- Multimodal emotion integration (face 60% + voice 40%)
- LSTM prediction fallback (moving average)
- Reliability test logging and reporting
- Streamlit UI with Thingswell branding

---

## Recommended Environment

| Item | Requirement |
|------|-------------|
| OS | Windows 11 (Windows 10 also supported) |
| Python | **3.11** (⚠️ 3.13 미검증) |
| Camera | USB or built-in webcam |
| Microphone | USB, built-in, or headset |
| Internet | For first STT model download only |
| RAM | 8GB minimum (16GB recommended) |
| Storage | 5GB free space |
| GPU | Not required (CPU mode default) |
| STT Engine | faster-whisper (default, Windows compatible) |

---

## Installation

```cmd
REM 1. Unzip the release package
REM 2. Navigate to scripts folder
cd emotion-recognition-beta-win64-v0.1.0-thingswell\release\scripts

REM 3. Install all dependencies (.venv auto-created)
install_all.bat

REM 4. Verify environment
health_check.bat

REM 5. Launch application
run_app.bat
```

---

## Test Procedure

### 순서 (권장)

| # | Step | Command / Action |
|---|------|-----------------|
| 1 | ZIP 압축 해제 | 탐색기에서 압축 해제 |
| 2 | Python 3.11 확인 | `python --version` |
| 3 | 전체 설치 | `release\scripts\install_all.bat` |
| 4 | 환경 검증 | `release\scripts\health_check.bat` |
| 5 | 앱 실행 | `release\scripts\run_app.bat` |
| 6 | 브라우저 접속 | http://localhost:8501 |
| 7 | minimal 모드 테스트 | UI 사이드바 → Minimal |
| 8 | face 모드 테스트 | 카메라 미리보기, 얼굴 감정 |
| 9 | voice 모드 테스트 | 마이크 입력, VAD, STT |
| 10 | full 모드 테스트 | 전체 기능 통합 |
| 11 | 로그 수집 | `release\scripts\collect_logs.bat` |
| 12 | 결과 전달 | test_report/ 폴더 압축 → hjlee@thingswell.co.kr |

### 카메라/마이크 권한 설정

Windows 설정 → 개인 정보 및 보안 → 카메라/마이크 → 앱 접근 허용

---

## Known Limitations

| # | Limitation | Note |
|---|-----------|------|
| 1 | STT 첫 실행 느림 | 모델 다운로드 (~40-250MB), 이후 캐시됨 |
| 2 | High Accuracy CPU 부하 | 고사양 PC 전용, 일반 노트북은 Standard 권장 |
| 3 | Voice emotion heuristic | 학습 모델 아님, 연구/데모 용도 |
| 4 | Python 3.13 미검증 | TensorFlow/DeepFace 호환 문제 가능 |
| 5 | openai-whisper optional | Windows 설치 실패 가능, faster-whisper 기본 |
| 6 | GPU 미사용 | CPU 모드 기본 (정상 동작) |
| 7 | 다중 얼굴 FPS 저하 | 1인 사용 기준 최적화 |

---

## Usage Restrictions

- ❌ 외부 무단 재배포 금지
- ❌ 역설계, 상업적 재판매 금지
- ❌ 의료, 법률, 채용, 고위험 의사결정 용도 금지
- ❌ 동의 없는 얼굴/음성 데이터 외부 전송 금지
- ✅ 내부 테스트, 연구, 데모 목적만 허용
- ✅ Thingswell Inc. 사전 서면 승인 필요 (재배포 시)

---

## Release Package Contents

```
emotion-recognition-beta-win64-v0.1.0-thingswell/
├── ui/                          # Streamlit UI
├── modules/                     # Core analysis modules
├── utils/                       # Utility functions
├── models/                      # Model files (if any)
├── release/
│   ├── scripts/                 # BAT scripts (8 files)
│   ├── README_TESTER.md
│   ├── TEST_CHECKLIST.md
│   ├── TROUBLESHOOTING.md
│   └── RELEASE_NOTES.md        # This file
├── version.py                   # Version metadata
├── config.py                    # Configuration
├── controller.py                # Pipeline controller
├── main.py                      # CLI entry point
├── README.md                    # Project overview
├── setup-guide.md               # Setup guide
├── privacy-notice.md            # Privacy policy
├── NOTICE.md                    # Legal notice
├── LICENSE-THINGSWELL.md        # Application license
├── requirements-minimal.txt     # Base dependencies
├── requirements-face.txt        # Face analysis
├── requirements-voice.txt       # Voice analysis
├── requirements-stt.txt         # STT (faster-whisper)
├── requirements-stt-openai-optional.txt
└── requirements.txt             # All dependencies
```

---

## Tester Feedback

테스트 완료 후 아래 내용을 hjlee@thingswell.co.kr로 전달해 주세요:

- 에러 발생 시 스크린샷
- `collect_logs.bat`으로 생성된 `test_report/` 폴더 (ZIP 압축)
- PC 환경 정보 (OS, Python 버전, RAM)
- 어떤 모드/프로파일에서 문제가 발생했는지

---

## GitHub Release 생성 방법

```
1. PR #1 merge (feature/project-documentation → main)
2. GitHub → Releases → "Create a new release"
3. Tag: beta-win64-v0.1.0
4. Title: Emotion Recognition Beta Windows v0.1.0 - Thingswell Inc.
5. Description: 이 파일 내용 복사
6. Asset 첨부: emotion-recognition-beta-win64-v0.1.0-thingswell.zip
7. Pre-release 체크
8. Publish
```

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| v0.1.0 | 2026 | Initial Beta Test Release — POC 완료, 신뢰성 시험 준비 |

---

## Contact

문의: hjlee@thingswell.co.kr  
웹사이트: https://thingswell.co.kr  

---

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.

본 소프트웨어는 내부 연구, 기능 검증, 신뢰성 시험, 성능 평가 및 데모 목적으로 제공됩니다.  
Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, 상업적 재판매, 외부 공개 배포를 금지합니다.



---

## Next Version Issues (다음 버전 후보)

> 아래 항목은 v0.1.0 POC에서 제외되었으며, 다음 버전 이슈로 분리합니다.

| # | Issue | Priority | Note |
|---|-------|----------|------|
| 1 | STT real-time trigger 개선 | High | VAD 정확도 향상, 짧은 발화 인식률 개선 |
| 2 | LSTM 모델 학습 및 평가 데이터셋 구축 | High | 현재 이동평균 폴백 사용 중 |
| 3 | 음성감정 trained model 적용 | Medium | 현재 heuristic baseline만 구현 |
| 4 | EXE/Installer 패키징 | Medium | PyInstaller 또는 cx_Freeze 기반 |
| 5 | Docker/내부 서버 배포 | Low | 내부 테스트 서버용 컨테이너 |
| 6 | 장시간 안정성 자동 테스트 | Medium | 1시간+ 연속 실행 자동화 |
| 7 | 개인정보 동의 UI 강화 | Medium | 최초 실행 시 동의 팝업 |
| 8 | 클라우드 배포 | Low | 현재 로컬 전용 |
| 9 | 인증/로그인 시스템 | Low | 다중 사용자 지원 시 필요 |
| 10 | 데이터베이스 저장 | Low | 현재 CSV/JSON 파일 기반 |

---
