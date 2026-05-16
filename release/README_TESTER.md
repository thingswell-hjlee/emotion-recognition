# Multimodal Emotion Recognition & Korean STT Monitor - Tester Guide

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  
문의: hjlee@thingswell.co.kr  

Copyright © 2026 Thingswell Inc. All rights reserved.

본 소프트웨어는 내부 연구, 기능 검증, 신뢰성 시험, 성능 평가 및 데모 목적으로 제공됩니다.  
Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, 상업적 재판매, 외부 공개 배포를 금지합니다.

---

## ⚠️ 테스트 전 필독 사항

### 개인정보 / 카메라 / 마이크 사용 안내

이 앱은 **카메라와 마이크**를 사용합니다.

- 테스트 전 반드시 **사용자 동의**를 받고 진행하세요.
- 테스트 중 생성되는 로그에는 장치 정보, 성능 정보, 분석 결과가 포함될 수 있습니다.
- 민감한 얼굴/음성 원본 데이터는 **저장하지 않는 것**을 기본 정책으로 합니다.
- 저장 기능을 추가할 경우 별도 동의가 필요합니다.

### 사용 제한 (반드시 준수)

- ❌ **외부 재배포 금지** — 허가 없이 제3자에게 전달하지 마세요.
- ❌ **얼굴/음성 데이터 외부 업로드 금지** — 동의 없이 외부로 전송하지 마세요.
- ❌ **의료, 법률, 채용, 고위험 의사결정 용도 금지** — 연구/데모 목적만 가능합니다.
- ❌ **역설계, 상업적 재판매 금지**

---

## 테스트 환경 요구사항

| 항목 | 요구사항 |
|------|----------|
| OS | **Windows 11** 권장 (Windows 10도 가능) |
| Python | **3.11** 권장 (⚠️ 3.13은 미검증) |
| Camera | USB 또는 내장 웹캠 |
| Microphone | USB, 내장, 또는 헤드셋 마이크 |
| Internet | STT 모델 최초 다운로드용 (이후 오프라인 가능) |
| RAM | 최소 8GB (권장 16GB) |
| Storage | 5GB 이상 여유 공간 |
| STT 엔진 | **faster-whisper** (기본, Windows 호환) |

> ⚠️ openai-whisper는 Windows에서 설치 실패할 수 있으므로 기본 포함하지 않습니다.  
> 필요 시: `pip install -r requirements-stt-openai-optional.txt`

---

## GitHub Release에서 다운로드하기

### 다운로드 절차

1. **GitHub Release 페이지 접속:**  
   https://github.com/thingswell-hjlee/emotion-recognition/releases

2. **최신 Release 확인:**  
   `Emotion Recognition Beta Windows v0.1.0 - Thingswell Inc.` 클릭

3. **Assets 섹션에서 ZIP 다운로드:**  
   `emotion-recognition-beta-win64-v0.1.0-thingswell.zip` 클릭하여 다운로드

4. **ZIP 압축 해제:**  
   다운로드된 ZIP 파일을 **단순한 영문 경로**에 압축 해제하세요.

> ⚠️ **경로 주의사항:**
> - OneDrive 동기화 폴더에 두면 설치 중 파일 잠금 오류가 발생할 수 있습니다.
> - 한글/특수문자/공백이 많은 경로에서는 일부 패키지 설치가 실패할 수 있습니다.
> - **권장 경로:** `C:\thingswell_test\`
> - 예: `C:\thingswell_test\emotion-recognition-beta-win64-v0.1.0-thingswell\`

5. **이후 설치 및 실행은 아래 Step by Step 절차를 따르세요.**

> 💡 최초 설치는 인터넷 연결이 필요하며, 5~15분 정도 소요됩니다.  
> 💡 최초 STT 모델 다운로드에도 추가 시간(1~5분)이 필요합니다.

---

## 설치 및 실행 절차 (Step by Step)

### Step 0: Python 3.11 설치 확인

```cmd
python --version
```

Python 3.11.x가 출력되어야 합니다.  
설치되어 있지 않으면: https://www.python.org/downloads/release/python-3119/  
설치 시 반드시 **"Add Python to PATH"** 체크하세요.

---

### Step 1: ZIP 다운로드 및 압축 해제

`emotion-recognition-beta-win64-v0.1.0-thingswell.zip` 파일을 받아서  
원하는 위치에 압축 해제하세요.

> 💡 경로에 한글이나 공백이 있으면 오류가 발생할 수 있습니다.  
> 권장: `C:\Projects\emotion-recognition-beta-win64-v0.1.0-thingswell\`

---

### Step 2: 설치 (최초 1회)

**명령 프롬프트(cmd)** 또는 **PowerShell**을 열고:

```cmd
cd C:\Projects\emotion-recognition-beta-win64-v0.1.0-thingswell
cd release\scripts
install_all.bat
```

> 이 스크립트가 자동으로 수행하는 작업:
> 1. `.venv` 가상환경 생성
> 2. pip 업그레이드
> 3. requirements-minimal.txt 설치 (Streamlit, OpenCV 등)
> 4. requirements-face.txt 설치 (DeepFace)
> 5. requirements-voice.txt 설치 (librosa, sounddevice)
> 6. requirements-stt.txt 설치 (faster-whisper)

설치에 약 5~15분 소요됩니다 (인터넷 속도에 따라 다름).

---

### Step 3: 환경 검증

```cmd
health_check.bat
```

PASS 항목을 확인하세요.  
SKIP 항목은 optional 모듈이므로 minimal mode에서는 영향 없습니다.

---

### Step 4: 앱 실행

```cmd
run_app.bat
```

성공하면 브라우저가 자동으로 열리며 아래 주소에 접속됩니다:

> **http://localhost:8501**

브라우저가 자동으로 열리지 않으면 위 주소를 직접 입력하세요.

---

### Step 5: 테스트 진행

#### 테스트 순서 (권장)

| # | 모드 | 확인 사항 |
|---|------|-----------|
| 1 | **minimal** (기본) | 앱 실행, UI 표시, 더미 감정 결과 |
| 2 | **face** | 카메라 미리보기, 얼굴 감정 인식 |
| 3 | **voice** | 마이크 입력, VAD, STT 텍스트 표시 |
| 4 | **full** | 전체 기능 통합 동작 |

#### Windows 카메라/마이크 권한 설정

앱 실행 전 Windows에서 권한을 허용해야 합니다:

1. **설정** (Win+I) → **개인 정보 및 보안** → **카메라** → 켜기
2. **설정** (Win+I) → **개인 정보 및 보안** → **마이크** → 켜기
3. "데스크톱 앱의 카메라/마이크 액세스 허용" → **켜기**

---

### Step 6: 오류 발생 시

```cmd
health_check.bat
```

위 명령으로 누락 모듈을 확인하세요.  
자세한 해결 방법: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

### Step 7: 테스트 완료 후 로그 수집

```cmd
collect_logs.bat
```

실행하면 `test_report/` 폴더가 생성되며 아래 파일이 포함됩니다:
- `system_info.txt` — PC/OS/Python 정보
- `test_report_summary.json` — 버전/회사 메타데이터
- `performance_metrics.csv` — 성능 측정 (헤더)
- `reliability_events.csv` — 안정성 이벤트 (헤더)

---

### Step 8: 결과 전달

생성된 `test_report/` 폴더를 압축하여 전달하세요.

**전달처:** hjlee@thingswell.co.kr

**전달 시 포함할 정보:**
- 테스터 이름
- PC 이름 및 OS 버전
- 테스트 일시
- 발견된 문제점 (있으면)
- 재현 절차
- 스크린샷 (가능하면)

---

## 앱 중지 방법

- 브라우저에서 탭을 닫아도 서버는 계속 실행됩니다.
- 명령 프롬프트에서 **Ctrl+C**를 눌러 서버를 중지하세요.

---

## 디렉토리 구조 요약

```
emotion-recognition-beta-win64-v0.1.0-thingswell/
├── release/
│   ├── scripts/
│   │   ├── install_all.bat      ← 전체 설치
│   │   ├── install_minimal.bat  ← 최소 설치
│   │   ├── install_face.bat     ← 얼굴 모듈
│   │   ├── install_voice.bat    ← 음성 모듈
│   │   ├── install_stt.bat      ← STT 모듈
│   │   ├── run_app.bat          ← 앱 실행
│   │   ├── health_check.bat     ← 환경 검증
│   │   └── collect_logs.bat     ← 로그 수집
│   ├── README_TESTER.md         ← 이 문서
│   ├── TEST_CHECKLIST.md
│   ├── TROUBLESHOOTING.md
│   └── RELEASE_NOTES.md
├── ui/app.py                    ← Streamlit 앱
├── version.py                   ← 버전 정보
├── README.md
├── setup-guide.md
├── privacy-notice.md
├── NOTICE.md
├── LICENSE-THINGSWELL.md
└── requirements-*.txt           ← 의존성 파일들
```

---

## FAQ

**Q: minimal mode는 뭔가요?**  
A: 카메라+UI만 동작하는 기본 모드입니다. 인터넷 없이도 실행 가능합니다.

**Q: GPU가 없으면 안 되나요?**  
A: GPU 없이도 정상 동작합니다. CPU 모드로 자동 실행됩니다.

**Q: 첫 실행이 느린데 정상인가요?**  
A: STT 모델을 최초 다운로드하는 중입니다 (약 40~250MB). 이후에는 빠릅니다.

**Q: 카메라가 안 열려요.**  
A: 다른 앱(Zoom, Teams)이 카메라를 점유 중인지 확인하세요.  
   사이드바에서 카메라 인덱스를 0→1→2로 변경해 보세요.

---

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr  
Website: https://thingswell.co.kr
