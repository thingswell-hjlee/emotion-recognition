# Multimodal Emotion Recognition & Korean STT Monitor - Tester Guide

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  
문의: hjlee@thingswell.co.kr  

Copyright © 2026 Thingswell Inc. All rights reserved.

본 소프트웨어는 내부 연구, 기능 검증, 신뢰성 시험, 성능 평가 및 데모 목적으로 제공됩니다.  
Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, 상업적 재판매, 외부 공개 배포를 금지합니다.

---

## 테스터 안내 / Tester Information

이 문서는 Beta Test Release의 테스터를 위한 안내서입니다.

---

## ⚠️ 개인정보 / 카메라 / 마이크 사용 안내

### 한국어

이 앱은 카메라와 마이크를 사용합니다.  
테스트 전 사용자 동의를 받고 진행하세요.  
테스트 중 생성되는 로그에는 장치 정보, 성능 정보, 분석 결과가 포함될 수 있습니다.  
민감한 얼굴/음성 원본 데이터는 저장하지 않는 것을 기본 정책으로 하며,
저장 기능을 추가할 경우 별도 동의가 필요합니다.

### English

This application uses a camera and microphone.  
Please obtain user consent before testing.  
Generated logs may include device information, performance metrics, and analysis results.  
By default, raw face/audio data should not be stored.
If raw data recording is added, explicit consent is required.

---

## 테스트 환경 요구사항 / Test Environment

| 항목 | 요구사항 |
|------|----------|
| OS | Windows 10/11 (64-bit) |
| Python | 3.11+ |
| Camera | USB 또는 내장 웹캠 |
| Microphone | USB, 내장, 또는 헤드셋 |
| Internet | STT 모델 최초 다운로드용 |
| RAM | 최소 8GB (권장 16GB) |
| Storage | 5GB 이상 여유 공간 |

---

## 설치 및 실행 / Installation & Run

### Step 1: ZIP 압축 해제

`emotion-recognition-beta-win64-v0.1.0-thingswell.zip`을 원하는 위치에 압축 해제하세요.

### Step 2: 설치

```cmd
cd emotion-recognition-beta-win64-v0.1.0-thingswell
cd release\scripts
install_all.bat
```

### Step 3: 환경 검증

```cmd
health_check.bat
```

### Step 4: 앱 실행

```cmd
run_app.bat
```

---

## 테스트 항목 / Test Areas

1. **카메라 미리보기** - 카메라 영상이 정상 출력되는지 확인
2. **얼굴 감정 인식** - 표정 변화에 따른 감정 분류 확인
3. **음성 활동 감지** - 말할 때 VAD가 활성화되는지 확인
4. **한국어 STT** - 한국어 발화가 텍스트로 변환되는지 확인
5. **음성 감정 분석** - 음성 톤에 따른 감정 표시 확인
6. **성능 프로파일** - 각 모드(Balanced/High/Low) 전환 및 동작 확인
7. **장시간 안정성** - 30분 이상 연속 실행 시 크래시/메모리 누수 확인

---

## 로그 수집 / Log Collection

테스트 완료 후 로그를 수집하세요:

```cmd
cd release\scripts
collect_logs.bat
```

수집된 로그는 `test_report/` 폴더에 저장됩니다.

---

## 문제 발생 시 / If Issues Occur

1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 참조
2. `health_check.bat` 실행
3. 로그 수집 후 담당자에게 전달
4. 문의: hjlee@thingswell.co.kr

---

## 사용 제한 / Usage Restrictions

- 내부 테스트 목적으로만 사용하세요.
- 허가 없이 재배포하지 마세요.
- 동의 없이 얼굴/음성 데이터를 외부로 업로드하지 마세요.
- 의료, 법률, 채용 또는 고위험 의사결정에 사용하지 마세요.

---

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr  
Website: https://thingswell.co.kr
