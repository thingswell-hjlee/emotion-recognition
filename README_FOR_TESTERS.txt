════════════════════════════════════════════════════
 Thingswell Inc.
 Multimodal Emotion Recognition & Korean STT Monitor
 Beta Test Release v0.1.0
════════════════════════════════════════════════════

[ 빠른 시작 ]

1. 이 폴더의 START.bat 를 더블클릭하세요.
2. 설치와 실행이 자동으로 진행됩니다.
3. 최초 설치는 5~30분 걸릴 수 있습니다 (인터넷 필요).
4. 브라우저에서 http://localhost:8501 이 열리면 테스트하세요.
5. minimal → face → voice → full 순서로 테스트하세요.
6. 테스트 후 release\scripts\collect_logs.bat 를 실행하세요.
7. 생성된 test_report 폴더를 개발팀에 전달하세요.

[ 주의 사항 ]

- Windows 11 권장
- Python 3.11 필요 (없으면 START.bat가 설치 안내를 표시합니다)
- Python 3.13은 미검증 — 사용하지 마세요
- 카메라/마이크 Windows 권한 허용 필요
  (설정 > 개인정보 > 카메라/마이크 > 앱 접근 허용)
- 테스트 전 사용자 동의 필요
- 외부 재배포 금지

[ 하지 말아야 할 것 ]

- git pull, git checkout 등 Git 명령 사용 금지
- make_release_zip.ps1 실행 금지 (개발자 전용)
- release\scripts 안의 BAT를 개별 실행하기 전에
  반드시 START.bat를 먼저 실행하세요 (.venv 생성 필요)

[ 문제 발생 시 ]

- release\scripts\collect_logs.bat 실행
- 생성된 test_report 폴더를 압축하여 전달
- 연락처: hjlee@thingswell.co.kr

[ 경로 권장 ]

- 권장: C:\thingswell_test\
- 피하세요: OneDrive 폴더, 한글/특수문자 많은 경로, 네트워크 드라이브

════════════════════════════════════════════════════
 Copyright (c) 2026 Thingswell Inc. All rights reserved.
 내부 연구/기능검증/신뢰성시험/성능평가/데모 목적 전용
════════════════════════════════════════════════════
