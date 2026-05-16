# Multimodal Emotion Recognition & Korean STT Monitor - Troubleshooting

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  
문의: hjlee@thingswell.co.kr  

Copyright © 2026 Thingswell Inc. All rights reserved.

본 소프트웨어는 내부 연구, 기능 검증, 신뢰성 시험, 성능 평가 및 데모 목적으로 제공됩니다.  
Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, 상업적 재판매, 외부 공개 배포를 금지합니다.

---

## Python 버전 문제

### Python 3.13 사용 시 문제

**증상:** TensorFlow, DeepFace 등이 설치 실패하거나 import 오류 발생

**원인:** Python 3.13은 TensorFlow/DeepFace 호환 미검증 상태입니다.

**해결:**
1. Python 3.11을 설치하세요: https://python.org/downloads/
2. 설치 시 "Add Python to PATH" 체크 필수
3. 기존 `.venv` 삭제 후 `install_minimal.bat` 재실행
4. `python --version`으로 3.11.x 확인

> ⚠️ Python 3.12/3.13은 이 배포판에서 공식 지원하지 않습니다.  
> Python 3.11을 권장합니다.

---

## numpy 설치 실패

**증상:** `pip install numpy` 시 빌드 에러 또는 호환성 오류

**해결:**
1. pip 업그레이드: `python -m pip install --upgrade pip`
2. 특정 버전 설치: `pip install numpy>=1.26.0,<2.0.0`
3. Python 3.11 사용 여부 확인 (3.13에서 numpy 2.x 충돌 가능)
4. 가상환경 삭제 후 재설치:
   ```cmd
   rmdir /s /q .venv
   install_minimal.bat
   ```

---

## openai-whisper 설치 실패

**증상:** `pip install openai-whisper` 시 빌드 에러, ffmpeg 미설치 에러

**원인:** openai-whisper는 Windows에서 추가 빌드 도구와 ffmpeg이 필요합니다.

**해결 (권장):**
- openai-whisper 대신 **faster-whisper**를 사용하세요 (기본 설치됨).
- 이 배포판은 faster-whisper가 기본 STT 엔진입니다.
- openai-whisper는 optional이며 `requirements-stt-openai-optional.txt`로 분리됩니다.

**그래도 openai-whisper를 설치하려면:**
1. ffmpeg 설치: https://ffmpeg.org/download.html → PATH에 추가
2. Microsoft C++ Build Tools 설치
3. `pip install -r requirements-stt-openai-optional.txt`

---

## faster-whisper 관련 문제

### 모델 다운로드가 안 됩니다

**해결:**
1. 인터넷 연결 확인
2. 방화벽/프록시가 huggingface.co를 차단하는지 확인
3. 첫 실행 시 tiny 모델(~40MB)이 자동 다운로드됩니다
4. 다운로드 완료 후에는 오프라인 사용 가능

### STT가 비활성화 상태입니다

**해결:**
1. 사이드바에서 "STT 사용" 토글이 ON인지 확인
2. voice 또는 full 모드인지 확인 (minimal/face 모드에서는 STT 비활성)
3. health_check.bat에서 faster-whisper가 PASS인지 확인
4. 아니라면: `install_stt.bat` 실행

### 말했는데 인식이 안 됩니다

**해결:**
1. UI에서 RMS 값이 0.01 이상인지 확인 (마이크 입력 있음)
2. VAD 상태가 SPEECH_ACTIVE로 변하는지 확인
3. noise_floor보다 RMS가 높은지 확인
4. 주변 소음을 줄이고 마이크에 가까이 말하세요
5. STT Model을 "tiny"에서 "base"로 변경 시도

---

## 카메라 문제 / Camera Issues

### 카메라를 열 수 없습니다

**증상:** 카메라 미리보기 화면이 검정색이거나 에러 표시

**해결:**
1. 다른 앱(Zoom, Teams, OBS 등)에서 카메라를 사용 중인지 확인하고 종료
2. Windows 설정 → 개인정보 및 보안 → 카메라 → 앱 접근 허용 확인
3. "데스크톱 앱의 카메라 액세스 허용" → **켜기**
4. 장치 관리자에서 카메라 드라이버 상태 확인
5. USB 카메라인 경우 재연결
6. UI 사이드바에서 카메라 인덱스를 0 → 1 → 2 변경

### 카메라 권한이 거부됩니다

**해결:**
1. Windows 키 + I → 개인 정보 및 보안 → 카메라
2. "앱에서 카메라에 액세스하도록 허용" → **켜기**
3. "데스크톱 앱의 카메라 액세스 허용" → **켜기**
4. PC를 재시작하고 다시 시도

---

## 마이크 문제 / Microphone Issues

### 마이크를 인식하지 못합니다

**해결:**
1. Windows 설정 → 시스템 → 소리에서 입력 장치가 선택되어 있는지 확인
2. Windows 설정 → 개인정보 → 마이크 접근 허용 확인
3. "데스크톱 앱의 마이크 액세스 허용" → **켜기**
4. sounddevice 설치 확인: `pip install sounddevice`

### 마이크 권한이 거부됩니다

**해결:**
1. Windows 키 + I → 개인 정보 및 보안 → 마이크
2. "앱에서 마이크에 액세스하도록 허용" → **켜기**
3. "데스크톱 앱의 마이크 액세스 허용" → **켜기**

---

## STT 모델 로딩 지연

**증상:** 첫 실행 시 STT가 활성화되기까지 시간이 걸림

**원인:** faster-whisper 모델을 HuggingFace에서 최초 다운로드합니다.

| 모델 | 크기 | 다운로드 시간 (예상) |
|------|------|---------------------|
| tiny | ~40MB | 1~2분 |
| base | ~75MB | 2~5분 |
| small | ~250MB | 5~15분 |

**해결:**
- 정상 동작입니다. 첫 실행 시에만 발생합니다.
- 다운로드 완료 후 캐시되므로 이후에는 빠르게 로드됩니다.
- 인터넷 연결이 불안정하면 다운로드가 실패할 수 있습니다 → 재시작으로 재시도

---

## UI가 느린 경우

**해결:**
1. Low Resource (Low Power) 프로파일로 전환
2. face mode에서 High Accuracy → Standard로 변경
3. 다른 브라우저 탭/프로그램을 종료하여 CPU 부하 감소
4. full mode 대신 개별 모드(face 또는 voice)로 테스트

---

## High Accuracy 모드 CPU 부하 문제

**증상:** High Accuracy 프로파일 사용 시 PC가 느려짐, 팬 소음 증가

**원인:** 640x480 해상도 + 3프레임 스킵 + 8초 주기로 CPU 부하가 높습니다.

**해결:**
1. Standard 프로파일로 전환 (일반 사용에 충분)
2. Low Power 프로파일 사용 (노트북 배터리 절약)
3. High Accuracy는 고사양 데스크톱에서만 사용 권장
4. 전원에 연결된 상태에서만 사용

---

## 설치 문제 / Installation Issues

### BAT 파일이 실행되지 않습니다

**해결:**
1. 파일 탐색기에서 더블클릭하거나 cmd에서 직접 실행
2. Windows Defender/백신 프로그램이 차단했는지 확인
3. "속성" → "차단 해제" 체크 (다운로드된 파일의 경우)
4. 관리자 권한으로 cmd를 열고 BAT 경로를 직접 입력

### health_check.bat에서 FAIL 항목

**해결:**
1. FAIL 항목에 대응하는 설치 스크립트를 재실행:
   - streamlit/cv2/numpy FAIL → `install_minimal.bat`
   - deepface FAIL → `install_face.bat`
   - sounddevice/librosa FAIL → `install_voice.bat`
   - faster-whisper FAIL → `install_stt.bat`
2. 또는 전체 재설치: `install_all.bat`

### .venv 관련 문제

**해결:**
1. `.venv` 폴더 삭제: `rmdir /s /q .venv`
2. `install_minimal.bat` 재실행 (새로 .venv 생성)
3. Python PATH가 올바른지 확인: `where python`

---

## 앱이 응답하지 않습니다

**해결:**
1. 브라우저에서 Streamlit 탭을 새로고침 (F5)
2. 명령 프롬프트에서 Ctrl+C로 서버 종료 후 `run_app.bat` 재실행
3. 작업 관리자에서 python.exe 프로세스를 종료하고 재시작

---

## 도움 요청 / Getting Help

위 방법으로 해결되지 않을 경우:

1. `collect_logs.bat`을 실행하여 로그를 수집하세요.
2. `test_report/` 폴더를 ZIP으로 압축하여 전달하세요.
3. 문의: hjlee@thingswell.co.kr

**전달 시 포함할 정보:**
- 테스터 이름, PC 이름
- OS 버전 (Windows 10/11)
- Python 버전 (`python --version`)
- 에러 메시지 스크린샷
- 재현 절차 설명
- test_report/ 폴더 (ZIP)

---

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr  
Website: https://thingswell.co.kr
