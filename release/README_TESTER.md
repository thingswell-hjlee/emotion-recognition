# Multimodal Emotion Recognition & Korean STT Monitor - Tester Guide

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  
문의: hjlee@thingswell.co.kr  

Copyright © 2026 Thingswell Inc. All rights reserved.  
내부 연구/기능검증/신뢰성시험/성능평가/데모 목적 전용.  
Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, 상업적 재판매, 외부 공개 배포를 금지합니다.

---

## 1. Download (다운로드)

1. GitHub Release 페이지 접속:  
   https://github.com/thingswell-hjlee/emotion-recognition/releases

2. 최신 Release에서 **Assets** 섹션의 ZIP 다운로드:  
   `emotion-recognition-beta-win64-v0.1.0-thingswell.zip`

---

## 2. Extract (압축 해제)

ZIP을 **단순한 영문 경로**에 압축 해제하세요.

**권장 경로:** `C:\thingswell_test\`

> ⚠️ 피하세요:
> - OneDrive / Google Drive 동기화 폴더
> - 한글/특수문자가 많은 경로
> - 네트워크 드라이브
> - 공백이 많은 깊은 경로

---

## 3. Run (실행)

**`START.bat`를 더블클릭하세요.** 그것으로 끝입니다.

START.bat가 자동으로 수행하는 작업:
1. Python 3.11 확인 (없으면 설치 안내)
2. .venv 가상환경 생성
3. 필수 패키지 설치 (Streamlit, OpenCV, NumPy)
4. 선택 패키지 설치 (DeepFace, librosa, faster-whisper — 실패해도 계속 진행)
5. 환경 검증
6. Streamlit 앱 실행 → 브라우저에서 http://localhost:8501 자동 오픈

> 💡 최초 실행 시 5~30분 소요됩니다.  
> 💡 2회차부터는 이미 설치된 모듈을 스킵하므로 즉시 실행됩니다.

---

## 4. Test (테스트)

| # | 모드 | 확인 사항 |
|---|------|-----------|
| 1 | **minimal** | 앱 실행, UI 정상 표시 |
| 2 | **face** | 카메라 미리보기, 얼굴 감정 인식 |
| 3 | **voice** | 마이크 입력, VAD, STT 텍스트 |
| 4 | **full** | 전체 기능 통합 동작 |

### Windows 카메라/마이크 권한 설정

1. 설정 (Win+I) → 개인 정보 및 보안 → 카메라 → 켜기
2. 설정 (Win+I) → 개인 정보 및 보안 → 마이크 → 켜기
3. "데스크톱 앱의 카메라/마이크 액세스 허용" → 켜기

---

## 5. Collect Logs (로그 수집)

테스트 완료 후:

```cmd
release\scripts\collect_logs.bat
```

생성된 `test_report_YYYYMMDD_HHMMSS` 폴더를 ZIP으로 압축하여  
**hjlee@thingswell.co.kr** 로 전달하세요.

---

## 6. Do NOT do (하지 마세요)

| ❌ 하지 마세요 | 이유 |
|----------------|------|
| `git pull` / `git checkout` | 테스터 PC에서 Git 불필요 |
| `make_release_zip.ps1` 실행 | 개발자 전용 빌드 스크립트 |
| `release\scripts\install_all.bat` 먼저 실행 | START.bat가 자동 처리 |
| 시스템 Python에 직접 pip install | .venv 격리 깨짐 |

**항상 START.bat부터 실행하세요.**

---

## 테스트 환경 요구사항

| 항목 | 요구사항 |
|------|----------|
| OS | **Windows 11** 권장 (Windows 10도 가능) |
| Python | **3.11** 필수 (⚠️ 3.13은 미검증) |
| Camera | USB 또는 내장 웹캠 |
| Microphone | USB, 내장, 또는 헤드셋 |
| Internet | 최초 설치 시 필요 (이후 오프라인 가능) |
| RAM | 최소 8GB (권장 16GB) |
| Storage | 5GB 이상 여유 공간 |

---

## 사용 제한

- ❌ 외부 재배포 금지
- ❌ 얼굴/음성 데이터 외부 업로드 금지
- ❌ 의료, 법률, 채용, 고위험 의사결정 용도 금지
- ❌ 역설계, 상업적 재판매 금지
- ✅ 테스트 전 카메라/마이크 사용 동의 필요

---

## 문제 발생 시

1. `release\scripts\collect_logs.bat` 실행
2. 생성된 `test_report_*` 폴더를 ZIP 압축
3. hjlee@thingswell.co.kr 로 전달

---

**Thingswell Inc.** AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.
