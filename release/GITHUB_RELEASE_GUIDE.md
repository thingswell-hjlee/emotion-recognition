# GitHub Release 생성 절차 (관리자용)

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  
문의: hjlee@thingswell.co.kr  

---

## 개요

이 문서는 `emotion-recognition-beta-win64-v0.1.0-thingswell.zip` 배포판을  
GitHub Release로 공개하는 절차를 설명합니다.

---

## 사전 조건

- PR #1 (`feature/project-documentation` → `main`) merge 완료
- Windows PC에서 PowerShell 실행 가능
- GitHub 저장소 쓰기 권한 보유

---

## Step 1: 로컬 검수 및 ZIP 생성

```powershell
# 1. 최신 코드 체크아웃
cd C:\projects\emotion-recognition
git checkout main
git pull origin main

# 2. ZIP 생성
powershell -ExecutionPolicy Bypass -File .\make_release_zip.ps1

# 3. 결과 확인
dir dist\emotion-recognition-beta-win64-v0.1.0-thingswell.zip
```

정상 완료 시 아래가 출력됩니다:
- ZIP File: `emotion-recognition-beta-win64-v0.1.0-thingswell.zip`
- ZIP Path: `dist\emotion-recognition-beta-win64-v0.1.0-thingswell.zip`
- Total Files: (파일 수)

---

## Step 2: 로컬 설치 테스트 (권장)

ZIP을 별도 폴더에 압축 해제하고 설치/실행이 정상인지 확인합니다.

```powershell
# 테스트용 폴더에 압축 해제
Expand-Archive -Path dist\emotion-recognition-beta-win64-v0.1.0-thingswell.zip -DestinationPath C:\thingswell_test -Force

# 설치
cd C:\thingswell_test\emotion-recognition-beta-win64-v0.1.0-thingswell\release\scripts
.\install_all.bat

# 환경 검증
.\health_check.bat

# 앱 실행 (Ctrl+C로 종료)
.\run_app.bat
```

---

## Step 3: GitHub Release 생성

### 웹 UI 방식

1. https://github.com/thingswell-hjlee/emotion-recognition/releases 접속
2. **"Draft a new release"** 또는 **"Create a new release"** 클릭
3. 아래 정보 입력:

| 항목 | 값 |
|------|-----|
| **Tag** | `beta-win64-v0.1.0` (Create new tag on publish) |
| **Target** | `main` |
| **Title** | `Emotion Recognition Beta Windows v0.1.0 - Thingswell Inc.` |
| **Description** | `release/RELEASE_NOTES.md` 내용 복사 붙여넣기 |
| **Pre-release** | ✅ 체크 |

4. **Assets** 섹션에서 파일 첨부:
   - `dist/emotion-recognition-beta-win64-v0.1.0-thingswell.zip` 업로드

5. **"Publish release"** 클릭

### gh CLI 방식 (대안)

```bash
gh release create beta-win64-v0.1.0 \
  --title "Emotion Recognition Beta Windows v0.1.0 - Thingswell Inc." \
  --notes-file release/RELEASE_NOTES.md \
  --prerelease \
  dist/emotion-recognition-beta-win64-v0.1.0-thingswell.zip
```

---

## Step 4: Release URL 확인

생성된 Release URL:
```
https://github.com/thingswell-hjlee/emotion-recognition/releases/tag/beta-win64-v0.1.0
```

Direct download URL (Asset):
```
https://github.com/thingswell-hjlee/emotion-recognition/releases/download/beta-win64-v0.1.0/emotion-recognition-beta-win64-v0.1.0-thingswell.zip
```

---

## Step 5: 테스터에게 배포

### 공유할 정보

테스터에게 아래 내용을 전달하세요:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Thingswell Inc.
Multimodal Emotion Recognition & Korean STT Monitor
Beta Test Release v0.1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다운로드:
https://github.com/thingswell-hjlee/emotion-recognition/releases/tag/beta-win64-v0.1.0

설치 및 실행:
1. ZIP 다운로드 후 C:\thingswell_test\ 에 압축 해제
2. release\scripts\install_all.bat 실행
3. release\scripts\health_check.bat 실행
4. release\scripts\run_app.bat 실행
5. 브라우저에서 http://localhost:8501 접속

테스트 순서:
minimal → face → voice → full

테스트 완료 후:
release\scripts\collect_logs.bat 실행 후
test_report 폴더를 hjlee@thingswell.co.kr 로 전달

주의:
- Python 3.11 필요 (3.13 미검증)
- 카메라/마이크 권한 허용 필요
- 외부 재배포 금지
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 6: 테스트 결과 회수

테스터로부터 받을 항목:
- `test_report/` 폴더 (ZIP 압축)
- 에러 스크린샷
- 발견 이슈 목록
- PC 환경 정보

회수 후 확인사항:
- `test_report_summary.json`의 version/company 정보 정확성
- `pip_freeze.txt`에서 의존성 정상 설치 여부
- `system_info.txt`에서 OS/Python 버전 확인

---

## GitHub Actions (자동 빌드)

`.github/workflows/build-windows-beta.yml` workflow가 설정되어 있습니다.

- **수동 트리거:** Actions → "Build Windows Beta Release" → "Run workflow"
- **자동 트리거:** `make_release_zip.ps1` 또는 `version.py` 변경 시 push

Artifact는 Actions 실행 결과에서 다운로드할 수 있습니다.

---

## 체크리스트

Release 생성 전 최종 확인:

- [ ] PR #1 merge 완료
- [ ] `make_release_zip.ps1` 실행 성공
- [ ] ZIP 파일명: `emotion-recognition-beta-win64-v0.1.0-thingswell.zip`
- [ ] 로컬 설치/실행 테스트 통과
- [ ] Tag: `beta-win64-v0.1.0`
- [ ] Title: `Emotion Recognition Beta Windows v0.1.0 - Thingswell Inc.`
- [ ] Pre-release 체크
- [ ] ZIP asset 첨부
- [ ] Release URL 접근 확인
- [ ] 테스터에게 URL 전달

---

**Thingswell Inc.**  
AI Solution Development Team  
Copyright © 2026 Thingswell Inc. All rights reserved.
