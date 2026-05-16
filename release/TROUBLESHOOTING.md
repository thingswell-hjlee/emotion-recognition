# Multimodal Emotion Recognition & Korean STT Monitor - Troubleshooting

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  
문의: hjlee@thingswell.co.kr  

Copyright © 2026 Thingswell Inc. All rights reserved.

본 소프트웨어는 내부 연구, 기능 검증, 신뢰성 시험, 성능 평가 및 데모 목적으로 제공됩니다.  
Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, 상업적 재판매, 외부 공개 배포를 금지합니다.

---

## 카메라 문제 / Camera Issues

### 카메라를 열 수 없습니다

**증상:** 카메라 미리보기 화면이 검정색이거나 에러 표시

**해결:**
1. 다른 앱(Zoom, Teams 등)에서 카메라를 사용 중인지 확인하고 종료
2. Windows 설정 → 개인정보 → 카메라 접근 허용 확인
3. 장치 관리자에서 카메라 드라이버 상태 확인
4. USB 카메라인 경우 재연결
5. UI 사이드바에서 카메라 인덱스를 0 → 1 → 2 변경

---

## 마이크 문제 / Microphone Issues

### 마이크를 인식하지 못합니다

**해결:**
1. Windows 설정 → 시스템 → 소리에서 입력 장치 확인
2. Windows 설정 → 개인정보 → 마이크 접근 허용 확인
3. PyAudio 설치 확인: `pip install pyaudio`

### PyAudio 설치 실패

**해결:**
1. Microsoft C++ Build Tools 설치
2. 또는: `pip install pipwin && pipwin install pyaudio`

---

## STT 문제 / Speech-to-Text Issues

### STT 모델 로드가 느립니다
- 정상 동작입니다. 첫 실행 시 Whisper 모델을 다운로드합니다 (~1-3GB).
- 인터넷 연결 상태를 확인하세요.

### STT 인식률이 낮습니다
1. 마이크를 입에 가까이 위치
2. 주변 소음 감소
3. High Accuracy 프로파일 사용

---

## 성능 문제 / Performance Issues

### CPU 사용률이 높습니다
1. Low Resource 프로파일로 전환
2. 다른 CPU 집약적 프로그램 종료

### 앱이 응답하지 않습니다
1. 브라우저에서 Streamlit 탭을 새로고침
2. 명령 프롬프트에서 Ctrl+C로 종료 후 재실행

---

## 설치 문제 / Installation Issues

### BAT 파일이 실행되지 않습니다
1. 명령 프롬프트를 관리자 권한으로 실행
2. Windows Defender/백신이 차단했는지 확인

### health_check.bat에서 FAIL 항목
1. FAIL 항목에 대응하는 설치 스크립트 재실행
2. `pip install -r requirements.txt`로 누락 패키지 설치

---

## 도움 요청 / Getting Help

위 방법으로 해결되지 않을 경우:

1. `collect_logs.bat`을 실행하여 로그를 수집하세요.
2. `test_report/` 폴더를 압축하여 전달하세요.
3. 문의: hjlee@thingswell.co.kr

---

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr
