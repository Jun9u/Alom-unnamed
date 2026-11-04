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

`main` 보호 규칙으로 CI 성공이 병합의 필수 조건입니다. 현재 검사는 Python·저장소 위주이며 프런트·백엔드 전용 검사·빌드는 기술 스택 확정 후 추가합니다. 유료 음성 API나 실제 사용자 음성은 CI에서 사용하지 않습니다.

## 현재 GitHub 협업 설정 (2026-11-04 확인)

- 공개 저장소. `main` 직접 변경 금지: PR과 CI 성공 필수, 사람 승인 필수 수 0명
- 미해결 리뷰 대화가 있으면 병합 불가. `main` 삭제·강제 Push 금지
- `main` 규칙은 Squash merge만 허용. Auto-merge와 병합 후 작업 브랜치 자동 삭제 활성화
- [CODEOWNERS](../.github/CODEOWNERS)로 영역별 리뷰어 지정. `@22011619` 계정은 현재 읽기 권한이므로 쓰기 권한 활성화 후 코드 소유자로 작동
- [CodeRabbit](../.coderabbit.yaml) 설치·연동 확인. 일반 PR 자동 리뷰 활성화, Draft PR은 자동 리뷰 제외
- 중요 변경은 [협업 규칙](../CONTRIBUTING.md)에 따라 사람 리뷰를 요청하되, GitHub에서 사람 승인을 강제하지는 않음

