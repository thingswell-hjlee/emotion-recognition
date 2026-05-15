# Multimodal Emotion State Monitor

노트북의 웹캠과 마이크를 통해 사용자의 얼굴 표정과 음성을 분석하여 감정 상태를 인식하고,
LSTM 기반 예측 및 음성 안내를 제공하는 로컬 실행 프로그램입니다.

## 주요 기능

- **표정 감정 분석**: 웹캠으로 얼굴을 감지하고 9가지 감정으로 분류
- **음성 감정 분석**: 마이크 음성의 톤, 에너지 등을 분석하여 감정 분류
- **멀티모달 통합**: 표정 + 음성 결과를 가중 평균으로 통합
- **주기적 평균 계산**: 5~20초 주기(기본 10초)로 감정 평균 산출
- **LSTM 감정 예측**: 시계열 데이터 기반 다음 감정 상태 예측
- **감정 변화 판단**: 평균값과 예측값을 비교하여 변화 방향 제공
- **음성 안내**: 감정 상태를 짧은 문장으로 음성 출력
- **설정 UI**: Streamlit 기반 실시간 모니터링 및 설정 조정

## 감정 분류 체계

| 감정 | 설명 |
|------|------|
| neutral | 무표정 / 중립 |
| happy | 행복 / 기쁨 |
| sad | 슬픔 |
| angry | 분노 |
| surprised | 놀람 |
| fearful | 공포 |
| disgusted | 혐오 |
| stressed | 스트레스 |
| calm | 평온 |

## 빠른 시작

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 실행 (UI 모드)
streamlit run ui/app.py
```

## 프로젝트 구조

```
emotion-recognition/
├── main.py                  # 엔트리포인트
├── config.py                # 전역 설정
├── controller.py            # 파이프라인 오케스트레이터
├── modules/                 # 핵심 모듈
│   ├── webcam.py            # 웹캠 캡처 + 얼굴 감지
│   ├── face_expression.py   # 표정 감정 분류
│   ├── microphone.py        # 마이크 오디오 수집
│   ├── voice_emotion.py     # 음성 감정 분류
│   ├── emotion_integrator.py # 멀티모달 통합
│   ├── emotion_averager.py  # 주기별 평균 계산
│   ├── lstm_predictor.py    # LSTM 예측
│   ├── emotion_comparator.py # 평균 vs 예측 비교
│   └── voice_feedback.py    # 음성 안내 (TTS)
├── ui/
│   └── app.py               # Streamlit UI
├── models/                  # 학습된 모델
├── utils/                   # 유틸리티
├── requirements.txt         # 패키지 의존성
└── docs/                    # 문서
    ├── requirements.md
    ├── architecture.md
    ├── ui-design.md
    └── ...
```

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.9+ |
| 영상처리 | OpenCV |
| 표정 분석 | DeepFace / MediaPipe |
| 음성 처리 | librosa |
| 오디오 캡처 | sounddevice / PyAudio |
| 음성 합성 | pyttsx3 |
| 딥러닝 | TensorFlow (LSTM) |
| UI | Streamlit |

## 개인정보 보호

- 모든 처리는 로컬 PC에서만 수행합니다.
- 웹캠 영상과 음성은 저장하지 않습니다.
- 외부 서버로 데이터를 전송하지 않습니다.
- 사용자가 시작 버튼을 누른 후에만 분석합니다.

자세한 내용은 [privacy-notice.md](privacy-notice.md)를 참고하세요.

## 문서

| 문서 | 설명 |
|------|------|
| [requirements.md](requirements.md) | 기능/비기능 요구사항 |
| [architecture.md](architecture.md) | 시스템 아키텍처 |
| [ui-design.md](ui-design.md) | UI 설계 |
| [emotion-analysis-design.md](emotion-analysis-design.md) | 표정 분석 설계 |
| [voice-analysis-design.md](voice-analysis-design.md) | 음성 분석 설계 |
| [lstm-prediction-design.md](lstm-prediction-design.md) | LSTM 예측 설계 |
| [data-structure.md](data-structure.md) | 데이터 구조 설계 |
| [task-list.md](task-list.md) | 구현 작업 목록 |
| [setup-guide.md](setup-guide.md) | 설치 가이드 |
| [privacy-notice.md](privacy-notice.md) | 개인정보 안내 |

## 면책 사항

> 감정 분석 결과는 참고용이며, 의학적·심리학적 진단이 아닙니다.
