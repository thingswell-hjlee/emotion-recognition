# GitHub Release 배포 가이드

제작: Thingswell Inc. AI Solution Development Team  
버전: Beta Test Release v0.1.0  

---

## 역할 구분

### 개발자 (관리자) — 이 문서의 대상

- 개발 PC에서 ZIP 생성
- Clean folder에서 START.bat 검수
- PR merge
- GitHub Release 생성 및 ZIP 업로드
- 테스터에게 Release URL 공유

### 테스터 — release/README_TESTER.md 참조

- Release URL에서 ZIP 다운로드
- 압축 해제
- START.bat 더블클릭
- 테스트 수행
- collect_logs.bat 실행 후 결과 전달

> ⚠️ 테스터는 git, PowerShell, make_release_zip.ps1을 사용하지 않습니다.

---

## 개발자 절차

### Step 1: ZIP 생성

```powershell
cd C:\projects\emotion-recognition
git checkout feature/project-documentation
git pull origin feature/project-documentation
powershell -ExecutionPolicy Bypass -File .\make_release_zip.ps1
```

결과: `dist\emotion-recognition-beta-win64-v0.1.0-thingswell.zip`

### Step 2: Clean Folder 검수

```powershell
Remove-Item -Recurse -Force C:\thingswell_test -ErrorAction SilentlyContinue
mkdir C:\thingswell_test
Expand-Archive -Path dist\emotion-recognition-beta-win64-v0.1.0-thingswell.zip -DestinationPath C:\thingswell_test -Force
cd C:\thingswell_test
.\START.bat
```

확인 사항:
- [ ] START.bat 실행 성공
- [ ] .venv 생성됨
- [ ] 앱 실행됨 (http://localhost:8501)
- [ ] minimal mode 동작
- [ ] Thingswell footer 표시

### Step 3: PR Merge

PR #1 (`feature/project-documentation` → `main`)을 GitHub에서 merge합니다.

### Step 4: GitHub Release 생성

1. https://github.com/thingswell-hjlee/emotion-recognition/releases
2. "Create a new release" 클릭
3. 입력:

| 항목 | 값 |
|------|-----|
| Tag | `beta-win64-v0.1.0` (Create new tag) |
| Target | `main` |
| Title | `Emotion Recognition Beta Windows v0.1.0 - Thingswell Inc.` |
| Description | `release/RELEASE_NOTES.md` 내용 복사 |
| Pre-release | ✅ 체크 |

4. Assets에 ZIP 파일 첨부:  
   `dist/emotion-recognition-beta-win64-v0.1.0-thingswell.zip`

5. "Publish release" 클릭

### Step 5: URL 확인

Release URL:
```
https://github.com/thingswell-hjlee/emotion-recognition/releases/tag/beta-win64-v0.1.0
```

Direct download:
```
https://github.com/thingswell-hjlee/emotion-recognition/releases/download/beta-win64-v0.1.0/emotion-recognition-beta-win64-v0.1.0-thingswell.zip
```

### Step 6: 테스터에게 공유

아래 메시지를 테스터에게 전달하세요:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Thingswell Inc.
Multimodal Emotion Recognition Beta v0.1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

다운로드:
https://github.com/thingswell-hjlee/emotion-recognition/releases/tag/beta-win64-v0.1.0

실행 방법:
1. ZIP 다운로드
2. C:\thingswell_test\ 에 압축 해제
3. START.bat 더블클릭
4. 브라우저에서 http://localhost:8501 테스트

테스트 후:
release\scripts\collect_logs.bat 실행
생성된 test_report 폴더를 hjlee@thingswell.co.kr 전달

요구사항:
- Python 3.11 (없으면 START.bat가 안내)
- Windows 11 권장
- 카메라/마이크 권한 허용
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## gh CLI 대안

```bash
gh release create beta-win64-v0.1.0 \
  --title "Emotion Recognition Beta Windows v0.1.0 - Thingswell Inc." \
  --notes-file release/RELEASE_NOTES.md \
  --prerelease \
  dist/emotion-recognition-beta-win64-v0.1.0-thingswell.zip
```

---

## 테스트 결과 회수

테스터로부터 받을 것:
- `test_report_*` 폴더 (ZIP)
- 에러 스크린샷
- 발견된 이슈 목록

확인 사항:
- `version_info.txt`의 버전 정보 정확성
- `pip_freeze.txt`에서 의존성 확인
- `health_check.txt`의 STATUS 확인

---

**Thingswell Inc.** Copyright © 2026. All rights reserved.
