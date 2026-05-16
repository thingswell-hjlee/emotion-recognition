# Voice Analysis Design v2 - Multimodal Emotion State Monitor

## 1. 아키텍처 개요

```
마이크 입력 → VAD → Feature 추출 → 감정 분류 → Confidence 필터 → 평균 계산
                ↓                                        ↓
         SILENCE_DETECTED                        confidence tier
         → 분석 건너뜀                            → 가중치 결정
         → 평균 제외                              → 평균 반영
```

## 2. 파이프라인 단계

| # | 단계 | 모듈 | 출력 상태 |
|---|------|------|-----------|
| 1 | 마이크 캡처 | microphone.py | MIC_READY / MIC_ERROR |
| 2 | 오디오 수집 | AudioRingBuffer | AUDIO_BUFFERING |
| 3 | 음성 활동 감지 | voice_activity_detector.py | VOICE_DETECTED / SILENCE / INSUFFICIENT |
| 4 | 특징 추출 | voice_features.py | FEATURE_EXTRACTED / FEATURE_ERROR |
| 5 | 감정 분류 | voice_emotion.py | EMOTION_CLASSIFIED / LOW_CONFIDENCE |
| 6 | 신뢰도 필터 | confidence tier | FILTER_PASS / FILTER_REJECT |
| 7 | 평균 계산 | voice_averager.py | VOICE_AVERAGE_READY / NO_DATA |
| 8 | LSTM 전달 | controller.py | (유효 평균 있을 때만) |
| 9 | UI 표시 | ui/app.py | 실시간 업데이트 |

## 3. Voice Activity Detection (VAD)

### 판별 기준 (다중 조건)

| 기준 | 기본값 | 설명 |
|------|--------|------|
| RMS threshold | 0.015 | 전체 RMS 기준 무음 판별 |
| Peak threshold | 0.05 | Peak amplitude 기준 |
| Min voice ratio | 0.20 | 주기 내 최소 발화 비율 |
| Min valid seconds | 2.0초 | 최소 유효 발화 시간 |
| Min consecutive frames | 3 | 연속 유효 프레임 수 |
| ZCR threshold | 0.08 | Zero Crossing Rate 기준 |

### 핵심 정책
- **무음이면 감정 분석을 수행하지 않음**
- **무음 상태에서 fearful, angry, happy, surprised 출력 금지**
- 발화 부족 시 INSUFFICIENT_VOICE_DATA → 평균에서 제외

## 4. 음성 감정 분류기

### 인터페이스 구조

```python
BaseVoiceEmotionClassifier (추상)
├── HeuristicVoiceEmotionClassifier (현재 기본)
├── TrainedVoiceEmotionClassifier (향후)
└── DummyVoiceEmotionClassifier (테스트)
```

### Heuristic 분류기 출력 제한 (MVP)

| 출력 감정 | 조건 | 신뢰도 |
|-----------|------|--------|
| neutral | 중간 에너지 + 안정 피치 | 0.60 |
| calm | 낮은 에너지 + 안정 피치 | 0.65 |
| stressed | 높은 에너지 + 큰 피치 변동 + 높은 ZCR | 0.50~0.75 |
| angry (low conf) | 높은 에너지 + 낮은 피치 | 0.40~0.60 |
| sad (low conf) | 낮은 에너지 + 느린 리듬 | 0.35~0.55 |

**억제되는 감정** (학습 모델 없이): happy, fearful, surprised, disgusted

## 5. Confidence Filtering

| 등급 | confidence 범위 | 가중치 | 평균 반영 |
|------|-----------------|--------|-----------|
| strong | ≥ 0.75 | 1.0 | ✅ |
| usable | ≥ 0.60 | 0.7 | ✅ |
| low | ≥ 0.40 | 0.2 | ⚠️ (낮은 가중치) |
| discard | < 0.40 | 0.0 | ❌ 제외 |

## 6. 통합 평균 (Full Mode)

| 조건 | face_weight | voice_weight |
|------|-------------|--------------|
| voice strong + high confidence | 0.70 | 0.30 |
| voice usable confidence | 0.85 | 0.15 |
| voice low confidence | 0.95 | 0.05 |
| voice 무음/데이터 부족 | 1.00 | 0.00 |

## 7. 로그 형식

```
[VOICE] MIC_READY device="LG gram Microphone" sr=16000
[VOICE] LEVEL rms=0.004 peak=0.018 dbfs=-42.1 silence=true
[VOICE] SKIPPED reason=silence valid_seconds=0.0
[VOICE] LEVEL rms=0.038 peak=0.210 dbfs=-23.4 silence=false
[VOICE] FEATURES rms=0.038 pitch_mean=184.2 pitch_std=22.1 zcr=0.07 centroid=1320
[VOICE] RESULT emotion=neutral confidence=0.68 mode=heuristic
[VOICE] FILTER status=usable weight=0.7
[FUSION] face=neutral voice=neutral face_w=0.85 voice_w=0.15 final=neutral
```

## 8. 향후 확장

- `TrainedVoiceEmotionClassifier`: RAVDESS/TESS 학습 모델 교체
- CNN/Transformer 기반 Mel spectrogram 분류
- 실시간 학습 (사용자 피드백 기반)
- 다국어 지원

## 9. 현재 제한사항

- Voice mode는 **heuristic baseline**입니다 (학습 모델 아님)
- happy/fearful/surprised는 학습 모델 없이 정확한 판별이 어려워 억제됩니다
- 음성 감정 인식의 상용 수준 정확도는 별도 학습 모델이 필요합니다
- 현재는 "무음 vs 발화 구분"과 "기본 감정 방향성"을 제공하는 MVP 수준입니다
