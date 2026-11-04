# 개발 환경과 GitHub 설정

## 로컬 Python 도구

Python 3.11 기준으로 Ruff(코드 검사·포맷), pre-commit(커밋 전 검사), pytest(테스트)를 사용합니다. 제품 실행 환경의 최종 버전을 정한 것은 아닙니다.

Windows PowerShell, 저장소 루트에서:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-dev.ps1
```

macOS/Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pre_commit install
.venv/bin/python -m pre_commit run --all-files
.venv/bin/python -m pytest
```

## 현재 CI 범위

[GitHub Actions](../.github/workflows/ci.yml)는 `main`에 push하거나 `main` 대상 PR을 만들거나 갱신할 때, 또는 수동 실행할 때 작동합니다.

- Python 3.11에서 의존성 설치
- `pre-commit run --all-files`: Ruff 검사·포맷과 녹음 파일·대용량 파일·흔한 비밀키 실수 검사
- `pytest`: 현재는 저장소 관리용 테스트. 실제 제품·발음 평가 모델의 성능 시험이 아님

CI는 결과를 표시할 뿐, 지금은 병합을 자동 차단하지 않습니다. 프런트·백엔드의 자체 검사·빌드는 해당 기술 스택 확정 후 추가합니다. 유료 음성 API나 실제 사용자 음성은 CI에서 사용하지 않습니다.

## GitHub에서 추가할 설정

- 공개 전환 전 현재 파일·커밋 이력에 비밀키·사용자 음성 등이 없는지 점검
- 공개 전환 후 `main`에 PR과 CI 성공·작성자 외 리뷰 승인 요구
- [협업 규칙](../CONTRIBUTING.md)의 실제 계정을 기준으로 CODEOWNERS 또는 리뷰어 자동 요청 설정
- Squash merge만 사용하고 병합 후 작업 브랜치 자동 삭제
- CodeRabbit GitHub 앱 설치 여부 확인 후 자동 리뷰 활성화(현재 [설정 파일](../.coderabbit.yaml)에는 비활성화)

팀원 초대는 진행했으며, 각 계정의 수락과 실제 접근 권한은 별도로 확인합니다. GitHub 관리 화면 설정과 저장소에 설정 파일을 두는 것은 별개입니다.
