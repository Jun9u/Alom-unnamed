# 초기 설정과 남은 작업

## 포함된 것

단일 저장소 폴더 구성, 브랜치·PR 규칙, 작업·오류 템플릿,
Python Ruff 검사·포맷, pre-commit 훅, GitHub Actions CI, 저장소 위생 검사와 테스트입니다.
프론트엔드·백엔드 프레임워크와 실제 AI 모델은 포함하지 않았습니다.

이 저장소는 준구님의 개인 비공개 저장소로 시작합니다.
설정 파일 반영과 GitHub 관리 화면의 설정은 별개입니다.
아래 미적용 항목을 확인하세요. 별도 ZIP 실행이나 저장소 생성 도우미는 필요하지 않습니다.

## 각 개발자가 할 일

Python 3.11이 설치되어 있어야 아래 개발 도구 설치를 실행할 수 있습니다.
Windows에서는 저장소 루트에서 다음 명령을 실행합니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-dev.ps1
```

이 실행은 로컬 가상환경을 만들고 검사 도구와 커밋 훅을 설치합니다.
전역 Python 패키지나 전역 PowerShell 실행 정책을 변경하지 않습니다.
VS Code에서는 추천 확장 프로그램을 설치하면 Python 저장 시 포맷 설정을 사용할 수 있습니다.

## 별도로 확인하거나 적용할 것

- 병합 설정: CONTRIBUTING의 운영안은 Squash merge입니다. 다른 병합 방식 금지와 병합 후 브랜치 자동 삭제는 GitHub Settings에서 별도 설정해야 합니다.
- 팀원 초대: 실제 GitHub 아이디 확인 후 저장소 Settings의 Collaborators에서 초대합니다.
- CODEOWNERS: 팀장의 계정을 전체 파일 담당자로 넣지 않았습니다. 실제 아이디와 역할 합의 후 추가합니다.
- 브랜치 보호: 요금제와 지원 기능을 확인해 PR 승인·CI 성공 조건을 별도 설정합니다.
- CodeRabbit: 설정만 준비했으며 자동 리뷰는 꺼져 있습니다. 앱 권한·요금을 확인하고
  해당 저장소에 설치한 뒤 `.coderabbit.yaml`의 `reviews.auto_review.enabled`를 `true`로 바꿉니다.
  설치와 자동 리뷰 활성화는 별도 동의가 필요한 작업입니다.
- 프론트·백엔드 검사: 기술 스택 확정 후 각 담당자가 추가합니다.
- 유료 계정, GPU 서버, 데이터셋 다운로드, 실제 음성 전송: 실행하지 않습니다.

CI의 성공은 설정 파일이 아니라 실제 Actions 실행 결과를 보고 확인하세요.
현재 테스트는 초기 저장소 검사 코드 테스트이며 발음 평가 기능 테스트가 아닙니다.

## 근거 문서

- GitHub 브랜치 보호: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- pre-commit: https://pre-commit.com/
- Ruff: https://docs.astral.sh/ruff/
- CodeRabbit 설정: https://docs.coderabbit.ai/reference/configuration

주요 개발 도구는 확인 가능한 버전으로 고정했습니다. 최신 버전이라는 주장은 하지 않습니다.
GitHub Actions는 준비 시 확인한 공식 저장소의 v6 커밋 SHA에 고정했습니다.
