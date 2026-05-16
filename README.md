# Multimodal Emotion State Monitor

노트북의 웹캠과 마이크를 통해 감정 상태를 인식하고, LSTM 예측 및 음성 안내를 제공하는 **로컬 실행** 프로그램입니다.

> ⚠️ **개인정보 보호**: 모든 영상/음성은 로컬 메모리에서만 처리되며, 저장·전송되지 않습니다.

## 지원 환경

| 항목 | 요구사항 |
|------|----------|
| OS | Windows 10/11 (LG gram 등 노트북 포함) |
| Python | **3.11 권장** (3.9~3.11 지원) |
| GPU | 불필요 (Intel Arc Graphics 환경에서도 CPU 모드 기본 실행) |
| 카메라 | 내장 웹캠 또는 USB 웹캠 |
| 마이크 | 내장 마이크 또는 외부 마이크 |

> ⚠️ Python 3.12/3.13은 TensorFlow/DeepFace 호환 문제로 권장하지 않습니다.

## Quick Start (Windows 11 PowerShell)

### 방법 1: 배치 파일 사용 (가장 쉬움)

```powershell
# 프로젝트 폴더로 이동
cd C:\Projects\emotion-recognition

# 1. 설치 (최초 1회)
.\setup_windows.bat

# 2. 실행
.\run_windows.bat
```

### 방법 2: 수동 설치

```powershell
cd C:\Projects\emotion-recognition

# 가상환경 생성 및 활성화
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# pip 업그레이드 + 최소 패키지 설치
python -m pip install --upgrade pip
pip install -r requirements-minimal.txt

# 실행 (브라우저에서 http://localhost:8501 열림)
streamlit run ui/app.py
```

### 방법 3: 전체 기능 설치

```powershell
# DeepFace, TensorFlow 포함 (표정 분석 활성화)
pip install -r requirements-face.txt

# 음성 분석 추가 (voice/full mode)
pip install -r requirements-voice.txt

# 한국어 STT 추가 (선택적)
pip install -r requirements-stt.txt
```

> 💡 각 기능은 독립적으로 설치 가능합니다. 미설치 모듈은 자동 비활성화됩니다.

### 단계별 설치 요약

```powershell
pip install -r requirements-minimal.txt   # UI + 카메라 (필수)
pip install -r requirements-face.txt      # 표정 분석 (DeepFace)
pip install -r requirements-voice.txt     # 음성 감정 분석 (librosa)
pip install -r requirements-stt.txt       # 한국어 STT (Whisper)
```

## 실행 모드

| 모드 | 설명 | 필요 패키지 |
|------|------|------------|
| **minimal** (기본) | 카메라+UI+더미 분석, 첫 실행 권장 | requirements-minimal.txt |
| face | 웹캠 표정 분석 (DeepFace) | + requirements-face.txt |
| voice | 마이크 음성 분석 + STT | + requirements-voice.txt (+ requirements-stt.txt) |
| full | 전체 기능 | 모두 설치 |

> 🟢 **초기 기본값은 minimal mode**입니다. 첫 실행 성공 후 UI에서 모드를 변경할 수 있습니다.
>
> ⚠️ **full mode 음성 분석**은 `librosa`와 `sounddevice`가 설치되어야 활성화됩니다.
> 미설치 시 음성 분석만 비활성화되고 나머지 기능은 정상 동작합니다.

## 성능 프로파일

UI 사이드바에서 성능 프로파일을 선택하여 CPU 부하를 조절할 수 있습니다.

| 프로파일 | 해상도 | 분석 주기 | 프레임 스킵 | 권장 환경 |
|----------|--------|-----------|-------------|-----------|
| 🔋 **Low Power** | 320x240 | 12초 | 10프레임 | 일반 노트북, 배터리 사용 시 |
| ⚡ **Standard** (기본) | 480x360 | 10초 | 5프레임 | 대부분의 PC |
| 🎯 **High Accuracy** | 640x480 | 8초 | 3프레임 | 고사양 데스크톱 |
| 🔧 **Debug** | 640x480 | 10초 | 5프레임 | 개발/테스트 (모듈 개별 ON/OFF) |

> 💡 **일반 노트북 (LG gram 등)에서는 Standard 또는 Low Power를 권장**합니다.
> Full mode + High Accuracy는 CPU 부하가 높으므로 고사양 PC에서 사용하세요.

### 결과 안정화

- 최근 3~5회 분석 결과의 **이동평균**을 적용하여 단일 프레임 노이즈를 제거합니다.
- Confidence가 60% 미만이면 **low confidence** 경고를 표시합니다.
- 단일 결과보다 **recent trend**를 우선하여 안정적인 감정 상태를 제공합니다.

## 주요 기능

- **라이브 카메라 프리뷰**: 웹캠 영상을 UI에 실시간 표시
- **표정 감정 분석**: 9가지 감정 분류 (DeepFace + 더미 폴백)
- **음성 감정 분석**: 음성 톤/에너지 기반 분류
- **한국어 STT**: Whisper 기반 음성→텍스트 변환 (로컬 실행)
- **멀티모달 통합**: 표정 60% + 음성 40% 가중 평균
- **LSTM 감정 예측**: 시계열 기반 예측 (모델 없으면 이동평균 폴백)
- **음성 안내**: pyttsx3 TTS (기본 OFF, 선택적 활성화)
- **결과 안정화**: 이동평균 + confidence threshold로 노이즈 제거
- **성능 프로파일**: 4단계 부하 조절 (Low Power ~ High Accuracy)
- **Streamlit UI**: 설정, 제어, 결과 표시, 실시간 상태 바

## 한국어 STT (음성 인식)

- OpenAI Whisper 또는 faster-whisper 기반 로컬 STT
- VAD가 유효 발화를 감지한 경우에만 STT 실행 (무음 시 실행 안 함)
- 모델 크기: tiny (~75MB) / base (~150MB) / small (~500MB)
- 기본값: base 모델 (CPU 환경 적합)
- 최초 실행 시 모델 자동 다운로드 (인터넷 필요)
- CPU 환경에서 small 이상은 느릴 수 있음 → 일반 노트북에서는 tiny/base 권장
- 외부 서버 전송 없음 (완전 로컬 처리)

## 개인정보 보호

- ❌ 웹캠 영상 저장 금지
- ❌ 얼굴 이미지 저장 금지
- ❌ 원본 음성 저장 금지
- ❌ 외부 서버 전송 금지
- ✅ 로컬 메모리 처리만 수행
- ✅ 감정 점수(숫자)만 로그 저장 가능

## Intel Arc Graphics 대응

- GPU 가속에 의존하지 않음 (CPU 모드 기본)
- TensorFlow GPU 경고가 출력되어도 앱은 정상 동작
- `config.py`에서 `force_cpu = True`로 설정됨

## 안정성 설계

- 모든 모듈에 try/except 적용 → 개별 모듈 실패해도 앱 계속 실행
- DeepFace 실패 → OpenCV Haar → 더미 neutral 반환 (3단계 폴백)
- LSTM 모델 파일 없음 → 이동평균 예측으로 폴백
- pyttsx3 실패 → 음성 안내만 비활성화 (텍스트 안내 유지)
- 카메라/마이크 접근 실패 → UI에 에러 표시 후 다른 기능 계속 실행
- 모드 전환 시 기존 리소스를 안전하게 stop → cleanup → 재초기화
- 슬라이더 값 변경 시 전체 재시작 없이 hot-update 적용

## 첫 실행 시 참고

- **Python 3.11 권장**: 3.12/3.13은 TensorFlow/DeepFace 호환 문제 있음
- **minimal mode**: 인터넷 연결 불필요, `requirements-minimal.txt`만으로 실행 가능
- **DeepFace (선택적)**: `pip install -r requirements.txt` 설치 후 face/full 모드 사용 가능
  - 첫 실행 시 감정 분석 모델 자동 다운로드 (~100MB, 인터넷 필요)
  - 모델 다운로드 실패 시 더미 모드로 자동 폴백
- **음성 분석 (선택적)**: `pip install librosa sounddevice` 추가 설치 후 voice/full 모드 사용
  - 미설치 시 음성 분석만 비활성화, 나머지 기능 정상 동작
- Windows 카메라/마이크 권한: 설정 > 개인 정보 > 카메라/마이크 허용 필요

## 프로젝트 구조

```
emotion-recognition/
├── main.py                  # CLI 엔트리포인트
├── config.py                # 전역 설정 (모드 + 프로파일)
├── performance_profiles.py  # 성능 프로파일 정의
├── controller.py            # 파이프라인 오케스트레이터
├── modules/                 # 핵심 모듈
├── ui/app.py                # Streamlit UI
├── utils/                   # 유틸리티 (smoothing, logger, timer)
├── models/                  # 모델 파일 (자동 생성)
├── logs/                    # 로그 파일 (자동 생성)
├── requirements.txt         # 전체 기능 패키지
├── requirements-minimal.txt # 최소 안정 패키지
├── setup_windows.bat        # Windows 설치 스크립트
└── run_windows.bat          # Windows 실행 스크립트
```

## 면책 사항

> 감정 분석 결과는 참고용이며, 의학적·심리학적 진단이 아닙니다.

## Troubleshooting: 앱은 실행되지만 감정 결과가 나오지 않는 경우

| # | 점검 항목 | 확인 방법 |
|---|-----------|-----------|
| 1 | face mode로 먼저 테스트 | 사이드바에서 모드를 "Face"로 변경 후 시작 |
| 2 | 카메라 영상 확인 | face_status가 "NO_FRAME"이면 카메라 권한/인덱스 확인 |
| 3 | 조명/얼굴 위치 | face_status가 "NO_FACE"이면 밝은 곳에서 정면 응시 |
| 4 | Standard 프로파일 사용 | Low Power는 분석 간격이 길어 결과 느림 → Standard로 변경 |
| 5 | confidence threshold 확인 | low confidence 표시되면 DeepFace가 동작 중인 것 (정상) |
| 6 | 로그 패널 확인 | "📊 분석 #1" 로그가 보이면 파이프라인 정상 |
| 7 | DeepFace 설치 확인 | `pip install deepface` 후 face mode 재시도 |
| 8 | minimal mode 테스트 | minimal은 더미 결과를 반환하므로 반드시 결과가 표시됨 |

## Troubleshooting: 음성 감정 결과가 불안정한 경우

| # | 점검 항목 | 확인 방법 |
|---|-----------|-----------|
| 1 | 무음 테스트 | voice/full 모드에서 아무 말도 하지 않고 10초 대기 → "무음" 상태 확인 |
| 2 | 마이크 입력 확인 | UI "마이크 입력 상태" 패널에서 RMS/peak 값 확인 |
| 3 | RMS 임계값 조정 | silence_threshold가 너무 낮으면 소음이 발화로 인식됨 |
| 4 | 유효 발화 확인 | voice_ratio > 0.20, valid_seconds > 2.0 인지 확인 |
| 5 | 분류기 모드 확인 | "음성 모델: heuristic baseline" → 학습 모델 아님 (정상) |
| 6 | confidence 확인 | low_confidence면 평균에서 낮은 가중치 적용 (정상) |
| 7 | full mode 가중치 | voice_weight가 0.0~0.30인지 확인 (무음이면 0.0) |
| 8 | librosa 설치 | `pip install librosa sounddevice` 필요 |

**핵심 원칙**: 무음 상태에서는 어떤 감정 결과도 생성되지 않습니다.
유효한 발화가 감지된 경우에만 음성 감정 분석이 수행됩니다.

**로그에 "SILENCE_DETECTED" 또는 "INSUFFICIENT_VOICE_DATA"가 보이면**: 정상 동작입니다.
**로그에 "EMOTION_CLASSIFIED"가 보이면**: 유효 발화 기반 분석이 수행된 것입니다.
