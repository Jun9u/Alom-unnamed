# Alom-unnamed

아롬 프로젝트 2팀의 한국어 발음 연습 지원 서비스 개발 준비 저장소입니다.
현재 저장소 이름은 임시 이름이며 서비스명 확정 후 변경할 수 있습니다.
**아직 앱이나 발음 평가 모델이 구현된 상태가 아닙니다.** 핵심 기능은 팀 회의에서 확정합니다.

## 처음 볼 문서

- [협업 규칙](CONTRIBUTING.md): 작업 시작, 브랜치, PR, 리뷰 분담
- [초기 설정과 남은 작업](docs/setup.md): 로컬 검사 설치와 GitHub 설정
- [연결 구조](docs/architecture.md): 프론트엔드·백엔드·AI의 역할
- [모델 검토 양식](docs/model-review.md)
- [데이터셋 검토 양식](docs/dataset-review.md)

## 폴더

| 위치 | 용도 |
|---|---|
| `frontend/` | 화면, 녹음, 녹음 상태 표시. 프레임워크 미정 |
| `backend/` | 요청 처리, 예문·기록 관리. 프레임워크 미정 |
| `ai/` | 모델 검증 실험. 서비스나 학습 모델은 아직 없음 |
| `docs/` | 개발 문서, 연결 규칙, 검토 양식 |
| `scripts/` | 저장소 검사 및 로컬 개발 환경 준비 |
| `tests/` | 초기 저장소 검사 코드의 테스트. 제품 기능 테스트가 아님 |

기획·회의의 결정은 기존 팀 Notion을 기준으로 합니다. 개발 작업은 GitHub Issues,
코드 검토는 PR(Pull Request, 코드 변경 검토 요청)에 기록합니다.
동일 작업의 진행 상태를 두 도구에서 중복 관리하지 않습니다.

## Python 개발 도구 준비

검사 환경은 Python 3.11을 기준으로 합니다. 제품의 최종 실행 환경을 확정한 것은 아닙니다.

Windows PowerShell에서:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-dev.ps1
```

macOS 또는 Linux에서:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pre_commit install
.venv/bin/python -m pre_commit run --all-files
.venv/bin/python -m pytest
```

GitHub 자동 검사는 업로드 후 Actions 실행 결과로 확인합니다.
설정 파일이 있다는 것만으로 검사가 통과했거나 병합 차단이 활성화된 것은 아닙니다.

## 안전 원칙

음성 원본, 실제 사용자 자료, 모델 가중치, 비밀키는 이 저장소에 올리지 않습니다.
`data/README.md`를 먼저 읽어주세요. 일반 CI(Continuous Integration, 지속적 통합 검사)는
유료 음성 API나 실제 사용자 데이터에 접근하지 않습니다.
AI 검토 도구의 제안은 사람이 검증하고, 분석 실패를 발음 0점으로 바꾸지 않습니다.
