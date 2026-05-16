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

- [ ] Python 3.11+ 설치 확인
- [ ] `install_all.bat` 정상 실행
- [ ] `health_check.bat` 모든 항목 PASS
- [ ] 앱 실행 (`run_app.bat`) 정상

---

## 기능 테스트 / Functional Tests

### 카메라 / Camera
- [ ] 카메라 미리보기 정상 표시
- [ ] 얼굴 인식 박스 표시
- [ ] 카메라 없을 때 적절한 에러 메시지

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
- [ ] 마이크 없을 때 적절한 에러 메시지

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

### Balanced Mode
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

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr
