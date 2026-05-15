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
pip install -r requirements.txt

# 음성 분석 추가 (full mode용, 선택적)
pip install librosa==0.10.1 sounddevice==0.4.7
```

> 💡 `librosa`와 `sounddevice`는 full mode 음성 분석에만 필요합니다.
> 미설치 시에도 표정 분석과 UI는 정상 동작합니다.

## 실행 모드

| 모드 | 설명 | 필요 패키지 |
|------|------|------------|
| **minimal** (기본) | 카메라+UI+더미 분석, 첫 실행 권장 | requirements-minimal.txt |
| face | 웹캠 표정 분석 (DeepFace) | requirements.txt |
| voice | 마이크 음성 분석 (librosa) | requirements.txt + `pip install librosa sounddevice` |
| full | 전체 기능 | requirements.txt + `pip install librosa sounddevice` |

> 🟢 **초기 기본값은 minimal mode**입니다. 첫 실행 성공 후 UI에서 모드를 변경할 수 있습니다.
>
> ⚠️ **full mode 음성 분석**은 `librosa`와 `sounddevice`가 설치되어야 활성화됩니다.
> 미설치 시 음성 분석만 비활성화되고 나머지 기능은 정상 동작합니다.

## 주요 기능

- **표정 감정 분석**: 9가지 감정 분류 (DeepFace + 더미 폴백)
- **음성 감정 분석**: 음성 톤/에너지 기반 분류
- **멀티모달 통합**: 표정 60% + 음성 40% 가중 평균
- **LSTM 감정 예측**: 시계열 기반 예측 (모델 없으면 이동평균 폴백)
- **음성 안내**: pyttsx3 TTS (기본 OFF, 선택적 활성화)
- **Streamlit UI**: 설정, 제어, 결과 표시

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
├── config.py                # 전역 설정 (실행 모드 포함)
├── controller.py            # 파이프라인 오케스트레이터
├── modules/                 # 핵심 모듈
├── ui/app.py                # Streamlit UI
├── utils/                   # 유틸리티
├── models/                  # 모델 파일 (자동 생성)
├── logs/                    # 로그 파일 (자동 생성)
├── requirements.txt         # 전체 기능 패키지
├── requirements-minimal.txt # 최소 안정 패키지
├── setup_windows.bat        # Windows 설치 스크립트
└── run_windows.bat          # Windows 실행 스크립트
```

## 면책 사항

> 감정 분석 결과는 참고용이며, 의학적·심리학적 진단이 아닙니다.
