# Setup Guide - Windows 11 안정 실행

## 1. 사전 요구사항

### 하드웨어
- CPU: Intel Core Ultra 7 / i5 이상
- RAM: 8GB 이상
- 웹캠: 노트북 내장 또는 USB
- 마이크: 노트북 내장 또는 외부
- GPU: 불필요 (Intel Arc Graphics는 CPU 모드로 동작)

### 소프트웨어
- **Python 3.11** (권장)
- ⚠️ Python 3.12/3.13은 TensorFlow/DeepFace 호환 문제로 **사용하지 마세요**

---

## 2. Windows 11 설치

### 방법 A: 배치 파일 (가장 쉬움)

```
setup_windows.bat    ← 더블 클릭 (설치)
run_windows.bat      ← 더블 클릭 (실행)
```

### 방법 B: PowerShell 수동 설치

```powershell
cd C:\Projects\emotion-recognition
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-minimal.txt
streamlit run ui/app.py
```

---

## 3. Windows 카메라 권한 설정

**Windows 11에서 카메라를 사용하려면:**

1. **설정** 앱 열기 (Win+I)
2. **개인 정보 및 보안** > **카메라** 이동
3. "앱에서 카메라에 액세스하도록 허용" → **켜기**
4. "데스크톱 앱의 카메라 액세스 허용" → **켜기**
5. 다른 프로그램(Zoom, Teams, OBS)이 카메라를 점유 중이면 먼저 종료

**카메라 연결 확인:**
```powershell
# 장치 관리자에서 확인
devmgmt.msc
# "카메라" 또는 "이미징 장치" 항목 확인
```

**카메라 인덱스 변경 (안 열리면):**
- UI 사이드바에서 카메라 인덱스를 0 → 1 또는 2로 변경

---

## 4. Windows 마이크 권한 설정

**Windows 11에서 마이크를 사용하려면:**

1. **설정** 앱 열기 (Win+I)
2. **개인 정보 및 보안** > **마이크** 이동
3. "앱에서 마이크에 액세스하도록 허용" → **켜기**
4. "데스크톱 앱의 마이크 액세스 허용" → **켜기**
5. **설정 > 시스템 > 소리** 에서 입력 장치 확인

**마이크 장치 목록 확인:**
```powershell
python -c "import sounddevice; print(sounddevice.query_devices())"
```

---

## 5. 문제 해결

### "카메라를 열 수 없습니다"
1. Windows 카메라 권한 확인 (위 3번 참고)
2. 다른 앱이 카메라 점유 중인지 확인
3. UI에서 카메라 인덱스를 0→1→2 변경
4. 장치 관리자에서 드라이버 상태 확인
5. 💡 카메라 실패해도 앱은 계속 실행됩니다

### "마이크를 열 수 없습니다"
1. Windows 마이크 권한 확인 (위 4번 참고)
2. sounddevice 재설치: `pip install --force-reinstall sounddevice`
3. 💡 마이크 실패해도 표정 분석/더미 분석은 계속 실행됩니다

### TensorFlow GPU 경고
```
Could not load dynamic library 'libcudart.so'
```
→ **정상입니다**. Intel Arc Graphics 환경에서 CPU 모드로 동작합니다.

### Streamlit 브라우저 안 열림
→ 수동으로 http://localhost:8501 접속

### DeepFace 모델 다운로드 실패
→ minimal 모드에서는 모델 없이 실행됩니다. 인터넷 연결 후 face 모드로 전환하세요.

---

## 6. 테스트 체크리스트

첫 실행 후 아래 항목을 확인하세요:

| # | 확인 항목 | 기대 결과 | 확인 |
|---|-----------|-----------|------|
| 1 | `streamlit run ui/app.py` 실행 | 브라우저에 UI 표시됨 | ☐ |
| 2 | Streamlit 화면 표시 | 설정 패널 + 결과 영역 보임 | ☐ |
| 3 | "시작" 버튼 클릭 | 분석 시작, 로그에 메시지 표시 | ☐ |
| 4 | 카메라 상태 표시 | 🟢 사용 중 또는 ⚪ 연결 실패 (앱 중단 없음) | ☐ |
| 5 | minimal mode 감정 결과 | neutral/calm 중심 더미 결과 표시됨 | ☐ |
| 6 | 감정 점수 차트 | 막대 그래프 표시됨 | ☐ |
| 7 | LSTM 예측 표시 | "데이터 수집 중" → 5주기 후 예측 표시 | ☐ |
| 8 | 음성 안내 OFF 기본 | 사이드바에서 음성 안내 OFF 상태 확인 | ☐ |
| 9 | 음성 안내 ON 전환 | ON 시 TTS 출력 (또는 "TTS 미사용" 로그) | ☐ |
| 10 | "정지" 버튼 클릭 | 분석 정지, 리소스 해제 | ☐ |
| 11 | 카메라 인덱스 변경 | 0→1→2 변경 시 앱 중단 없음 | ☐ |
| 12 | 오류 발생 시 | 앱 지속 실행, 로그에 오류 메시지만 표시 | ☐ |

---

## 7. 설정 커스터마이징

`config.py` 주요 설정:

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `run_mode` | `"minimal"` | 실행 모드 (minimal/face/voice/full) |
| `camera_device_id` | 0 | 카메라 인덱스 |
| `camera_fps` | 15 | 프레임 레이트 (낮을수록 안정) |
| `cycle_seconds` | 10 | 분석 주기 (5~20초) |
| `tts_enabled` | False | 음성 안내 ON/OFF |
| `force_cpu` | True | GPU 비사용 (CPU 강제) |
