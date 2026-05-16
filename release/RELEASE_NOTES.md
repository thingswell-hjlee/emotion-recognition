# Emotion Recognition Beta Windows v0.1.0

Produced by Thingswell Inc. AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.  
Contact: hjlee@thingswell.co.kr  

---

## Purpose

This release is for reliability testing, performance evaluation, and demonstration.

---

## Included Features

- Live camera preview
- Face emotion analysis (7 emotions: Happy, Sad, Angry, Surprise, Fear, Disgust, Neutral)
- Voice activity detection (VAD)
- Korean STT (Speech-to-Text using Whisper)
- Voice emotion baseline analysis
- Performance profiles (Balanced, High Accuracy, Low Resource)
- Reliability test logs and reporting

---

## Usage Restrictions

- Internal testing only
- Do not redistribute without permission
- Do not upload face/audio data externally without consent
- Do not use for medical, legal, hiring, or high-stakes decision making

---

## Recommended Environment

- Windows 11 (Windows 10 also supported)
- Python 3.11+
- Webcam (USB or built-in)
- Microphone (USB, built-in, or headset)
- Internet connection for first STT model download
- RAM: 8GB minimum (16GB recommended)

---

## Known Limitations

- STT model loading may take time on first run (model download ~1-3GB)
- High Accuracy mode may be CPU intensive
- Voice emotion is heuristic baseline (not production-grade)
- Results are for research/demo use only
- No GPU required, but GPU will improve performance if available

---

## Installation

```cmd
cd emotion-recognition-beta-win64-v0.1.0-thingswell
cd release\scripts
install_all.bat
health_check.bat
run_app.bat
```

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| v0.1.0 | 2026 | Initial Beta Test Release |

---

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  
문의: hjlee@thingswell.co.kr  

Copyright © 2026 Thingswell Inc. All rights reserved.

본 소프트웨어는 내부 연구, 기능 검증, 신뢰성 시험, 성능 평가 및 데모 목적으로 제공됩니다.  
Thingswell Inc.의 사전 서면 승인 없이 무단 복제, 재배포, 역설계, 상업적 재판매, 외부 공개 배포를 금지합니다.
