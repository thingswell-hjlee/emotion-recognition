# Multimodal Emotion Recognition & Korean STT Monitor - Test Checklist

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  
문의: hjlee@thingswell.co.kr  

Copyright © 2026 Thingswell Inc. All rights reserved.

본 소프트웨어는 내부 연구, 기능 검증, 신뢰성 시험, 성능 평가 및 데모 목적으로 제공됩니다.  
Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, 상업적 재판매, 외부 공개 배포를 금지합니다.

---

## 테스터 정보 / Tester Info

| 항목 | 내용 |
|------|------|
| 테스터명 | |
| PC 이름 | |
| OS 버전 | |
| Python 버전 | |
| 테스트 일시 | |
| 사용 프로파일 | |

---

## 설치 테스트 / Installation Tests

- [ ] Python 3.11+ 설치 확인 (`python --version`)
- [ ] `install_all.bat` 정상 실행 (에러 없이 완료)
- [ ] `.venv` 폴더 자동 생성됨
- [ ] `health_check.bat` — streamlit PASS
- [ ] `health_check.bat` — opencv PASS
- [ ] `health_check.bat` — numpy PASS
- [ ] 앱 실행 (`run_app.bat`) 정상 — 브라우저 열림

---

## 기능 테스트 / Functional Tests

### 카메라 / Camera
- [ ] 카메라 미리보기 정상 표시
- [ ] 얼굴 인식 박스 표시
- [ ] 카메라 없을 때 적절한 에러 메시지 (앱 중단 없음)

### 얼굴 감정 인식 / Face Emotion
- [ ] Happy 감정 인식
- [ ] Sad 감정 인식
- [ ] Angry 감정 인식
- [ ] Neutral 감정 인식
- [ ] 감정 확률 표시
- [ ] 다중 얼굴 감지

### 음성 활동 감지 / Voice Activity Detection
- [ ] 마이크 접근 정상
- [ ] 말할 때 VAD 활성화 표시
- [ ] 조용할 때 VAD 비활성화
- [ ] 마이크 없을 때 적절한 에러 메시지 (앱 중단 없음)

### 한국어 STT / Korean Speech-to-Text
- [ ] STT 모델 로드 완료 (첫 실행 시 다운로드)
- [ ] 한국어 발화 인식
- [ ] 인식 결과 텍스트 표시
- [ ] 인식 지연 시간 측정

### 음성 감정 / Voice Emotion
- [ ] 음성 감정 분석 결과 표시
- [ ] 긍정/부정/중립 톤 구분

---

## 성능 테스트 / Performance Tests

### Balanced Mode (Standard)
- [ ] CPU 사용률 확인 (기대: 중간)
- [ ] 응답 지연 확인
- [ ] FPS 확인

### High Accuracy Mode
- [ ] CPU 사용률 확인 (기대: 높음)
- [ ] 정확도 향상 여부 확인
- [ ] 메모리 사용량 확인

### Low Resource Mode
- [ ] CPU 사용률 확인 (기대: 낮음)
- [ ] 저사양에서 동작 확인
- [ ] 기능 제한 확인

---

## 안정성 테스트 / Reliability Tests

- [ ] 10분 연속 실행: 크래시 없음
- [ ] 30분 연속 실행: 크래시 없음
- [ ] 60분 연속 실행: 크래시 없음
- [ ] 메모리 사용량 안정 (지속 증가 없음)
- [ ] CPU 사용량 안정
- [ ] 에러 로그 확인

---

## 엣지 케이스 / Edge Cases

- [ ] 카메라를 분리한 상태에서 실행
- [ ] 마이크를 분리한 상태에서 실행
- [ ] 네트워크 없이 실행 (STT 모델 이미 다운로드된 경우)
- [ ] 낮은 조명에서 얼굴 인식
- [ ] 여러 사람이 동시에 카메라에 보일 때
- [ ] 소음 환경에서 STT

---

## 로그 수집 / Log Collection

테스트 완료 후:
1. `collect_logs.bat` 실행
2. `test_report/` 폴더 확인
3. 로그 파일을 담당자에게 전달

---

## 의견 및 이슈 / Notes & Issues

| # | 항목 | 상세 내용 | 심각도 |
|---|------|-----------|--------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

---

## POC 완료 체크리스트 / POC Completion Checklist

> 이 섹션은 개발팀이 beta 릴리즈 전 최종 확인하는 항목입니다.

### 배포 패키지 / Release Package

- [ ] `make_release_zip.ps1` 실행 가능 (PowerShell)
- [ ] ZIP 파일명에 "thingswell" 포함: `emotion-recognition-beta-win64-v0.1.0-thingswell.zip`
- [ ] ZIP 내 `version.py` 포함
- [ ] ZIP 내 `NOTICE.md` 포함
- [ ] ZIP 내 `LICENSE-THINGSWELL.md` 포함
- [ ] ZIP 내 `privacy-notice.md` 포함
- [ ] ZIP 내 `requirements-stt-openai-optional.txt` 포함
- [ ] ZIP 내 `release/scripts/` (8개 BAT 파일) 포함

### 앱 UI / Application UI

- [ ] 앱 실행 성공 (`streamlit run ui/app.py`)
- [ ] Thingswell footer 표시 (하단 고정, 다크모드 호환)
- [ ] Sidebar "제작 정보 / About" 패널 표시
- [ ] Debug/Test Mode에서 Build Info expander 표시
- [ ] 앱 상단 제품명 표시

### 기능 모드 진입 / Mode Access

- [ ] minimal mode 진입 — 더미 감정 표시
- [ ] face mode 진입 — 카메라 preview 동작
- [ ] voice mode 진입 — 마이크 메트릭 표시
- [ ] full mode 진입 — 전체 기능 통합
- [ ] STT 상태 표시 (model loaded / queue size)

### 스크립트 / Scripts

- [ ] `install_all.bat` — .venv 생성 후 전체 설치
- [ ] `health_check.bat` — PASS/FAIL 결과 표시
- [ ] `run_app.bat` — Streamlit 앱 실행
- [ ] `collect_logs.bat` — test_report/ 폴더 생성
- [ ] `collect_logs.bat` — system_info.txt 생성
- [ ] `collect_logs.bat` — test_report_summary.json 생성

### 문서 / Documentation

- [ ] README.md — Thingswell 저작권 헤더/푸터
- [ ] setup-guide.md — 설치 가이드 완비
- [ ] privacy-notice.md — 개인정보 처리 안내
- [ ] NOTICE.md — 법적 고지
- [ ] LICENSE-THINGSWELL.md — Application License Notice
- [ ] release/RELEASE_NOTES.md — 릴리즈 노트
- [ ] release/README_TESTER.md — 비개발자 테스터 가이드
- [ ] release/TEST_CHECKLIST.md — 이 문서
- [ ] release/TROUBLESHOOTING.md — 문제 해결 가이드

### GitHub / Repository

- [ ] PR #1 feature/project-documentation — merge 준비 완료
- [ ] 모든 파일 커밋됨
- [ ] GitHub Release 업로드 준비 (ZIP artifact)
- [ ] .github/workflows/build-windows-beta.yml 존재

### 버전 일관성 / Version Consistency

- [ ] version.py VERSION == "0.1.0"
- [ ] BAT 파일 배너 "v0.1.0" 표시
- [ ] make_release_zip.ps1 $Version == "0.1.0"
- [ ] RELEASE_NOTES.md "v0.1.0" 명시
- [ ] README.md "v0.1.0" 표시
- [ ] UI footer "v0.1.0" 표시

---

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr
