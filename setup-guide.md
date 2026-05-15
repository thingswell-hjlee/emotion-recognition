# Setup Guide - Multimodal Emotion State Monitor

## 1. 사전 요구사항

### 하드웨어
- CPU: Intel i5 / AMD Ryzen 5 이상 (i7/Ryzen 7 권장)
- RAM: 4GB 이상 (8GB 권장)
- 웹캠: 노트북 내장 또는 USB 웹캠
- 마이크: 노트북 내장 또는 외부 마이크
- 디스크: 3GB 이상 여유 공간
- GPU: 불필요 (있으면 가속 활용)

### 소프트웨어
- **Python 3.9, 3.10, 또는 3.11** (3.11 권장)
  - ⚠️ Python 3.12/3.13은 tensorflow, mediapipe 호환 문제로 권장하지 않음
- pip (Python 패키지 관리자)
- Git (선택사항)

### OS별 추가 요구사항

| OS | 추가 설치/설정 |
|----|---------------|
| Windows 10/11 | Visual C++ Redistributable, 설정 > 개인 정보 > 카메라/마이크 접근 허용 |
| macOS 12+ | 시스템 환경설정 > 보안 > 카메라/마이크 접근 허용, `portaudio` 설치 |
| Ubuntu 20.04+ | `libgl1-mesa-glx`, `libglib2.0-0`, `portaudio19-dev` |

---

## 2. 설치 방법

### Step 1: 프로젝트 다운로드

```bash
git clone https://github.com/thingswell-hjlee/emotion-recognition.git
cd emotion-recognition
```

### Step 2: 가상환경 생성

```bash
# 가상환경 생성
python -m venv venv

# 활성화
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
```

### Step 3: 의존성 설치

```bash
pip install -r requirements.txt
```

### OS별 추가 설치

**macOS (portaudio 필요):**
```bash
brew install portaudio
pip install pyaudio
```

**Ubuntu/Debian:**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
sudo apt-get install libgl1-mesa-glx libglib2.0-0
pip install pyaudio
```

**Windows (PyAudio 설치 문제 시):**
```bash
pip install pipwin
pipwin install pyaudio
```

### Step 4: 모델 준비 (선택사항)

DeepFace 모델은 최초 실행 시 자동으로 다운로드됩니다.  
인터넷 없는 환경에서 사용하려면 미리 다운로드하세요:

```bash
# DeepFace 모델 다운로드 (최초 실행 시 자동, 수동 시)
python -c "from deepface import DeepFace; print('Model ready')"
```

> LSTM 모델은 프로그램 실행 시 자동으로 초기화됩니다.  
> 별도의 학습 스크립트 실행은 필요하지 않습니다.

---

## 3. 실행 방법

### 기본 실행 (Streamlit UI)

> ⚠️ 반드시 프로젝트 루트 디렉토리(`emotion-recognition/`)에서 실행하세요.

```bash
cd emotion-recognition
streamlit run ui/app.py
```

브라우저에서 `http://localhost:8501` 이 자동으로 열립니다.

### CLI 실행 (UI 없이)

```bash
cd emotion-recognition
python main.py --no-ui
```

### 분석 모드 지정

```bash
python main.py --no-ui --mode face_only --cycle 10
```

---

## 4. 사용 방법

### 4.1 기본 사용 흐름

1. 프로그램 실행 후 UI 확인
2. **설정 조정** (선택):
   - 감정 인식 주기 (기본 10초)
   - 음성 볼륨 (기본 70%)
   - 분석 종류 (기본: 표정+음성 통합)
3. **"시작" 버튼** 클릭
4. 카메라/마이크가 활성화되고 분석 시작
5. 결과 영역에서 실시간 감정 상태 확인
6. **"정지" 버튼**으로 분석 중단

### 4.2 분석 모드 설명

| 모드 | 필요 장비 | 설명 |
|------|-----------|------|
| 표정만 | 웹캠 | 얼굴 표정만으로 감정 분류 |
| 음성만 | 마이크 | 음성 톤/에너지로 감정 분류 |
| 표정+음성 통합 | 웹캠+마이크 | 두 결과를 가중 평균 (표정 60%, 음성 40%) |

---

## 5. 문제 해결

### 카메라 관련

**증상**: "카메라를 열 수 없습니다"

**Windows 10/11:**
1. **설정 > 개인 정보 및 보안 > 카메라** 에서 "앱에서 카메라에 액세스하도록 허용" 활성화
2. 같은 페이지에서 "데스크톱 앱의 카메라 액세스 허용" 활성화
3. 다른 프로그램(Zoom, Teams, OBS)이 카메라를 점유 중인지 확인
4. `config.py`에서 `camera_device_id`를 `1`로 변경해 보기
5. 장치 관리자에서 카메라 드라이버 정상 여부 확인

**macOS:**
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 카메라 > 해당 앱(터미널/IDE) 허용
2. 앱 재시작

**Linux:**
1. `ls -la /dev/video*` 로 장치 확인
2. `sudo usermod -aG video $USER` 후 재로그인

### 마이크 관련

**증상**: "마이크를 열 수 없습니다"

**Windows 10/11:**
1. **설정 > 개인 정보 및 보안 > 마이크** 에서 "앱에서 마이크에 액세스하도록 허용" 활성화
2. 같은 페이지에서 "데스크톱 앱의 마이크 액세스 허용" 활성화
3. **설정 > 시스템 > 소리** 에서 입력 장치 선택 및 테스트
4. 다른 프로그램의 마이크 점유 확인

**macOS:**
1. 시스템 환경설정 > 보안 및 개인 정보 보호 > 마이크 > 해당 앱 허용

**Linux:**
1. `arecord -l` 로 마이크 장치 목록 확인
2. `pulseaudio` 또는 `pipewire` 설정 확인

**공통:**
- pyaudio 재설치: `pip install --force-reinstall pyaudio`
- sounddevice 재설치: `pip install --force-reinstall sounddevice`

### TensorFlow 관련

**증상**: GPU 경고 메시지 (동작에는 문제 없음)
```
Could not load dynamic library 'libcudart.so'
→ GPU 없는 환경에서 정상. CPU로 동작합니다.
```

### Streamlit 관련

**증상**: 브라우저가 자동으로 열리지 않음
```
해결: 수동으로 http://localhost:8501 접속
```

---

## 6. 설정 커스터마이징

`config.py` 주요 설정:

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `camera_device_id` | 0 | 카메라 장치 번호 |
| `cycle_seconds` | 10 | 분석 주기 (5~20초) |
| `face_weight` | 0.6 | 통합 시 표정 가중치 |
| `voice_weight` | 0.4 | 통합 시 음성 가중치 |
| `tts_volume` | 70 | TTS 볼륨 (0~100) |
| `lstm_min_data_points` | 5 | LSTM 예측 시작 최소 데이터 |
| `silence_threshold` | 0.01 | 무음 판단 임계값 |

---

## 7. 제거 방법

```bash
deactivate
rm -rf emotion-recognition
rm -rf ~/.deepface  # DeepFace 모델 캐시 (선택)
```
