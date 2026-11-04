# Alom-unnamed

한국어 발음 연습 지원 서비스 개발 저장소입니다. 이름·MVP·기술 스택·발음 평가 모델은 아직 확정 전이며, 제품 기능은 구현되지 않았습니다.

## 코드 구조

| 폴더 | 역할 |
|---|---|
| `frontend/` | 화면·녹음·실시간 표시 |
| `backend/` | API·예문·기록 처리 |
| `ai/` | 음성 분석 모델·실험 |
| `docs/` | 개발 문서·검토 양식 |
| `scripts/`, `tests/` | 개발 환경 검사와 테스트 |

## 시작하기

1. [협업 규칙](CONTRIBUTING.md)을 읽습니다.
2. [개발 환경 설정](docs/setup.md)에 따라 로컬 도구를 설치합니다.
3. GitHub Issue에 작업을 등록하고 연결된 브랜치에서 개발한 뒤 PR로 검토받습니다.

기획·팀 결정은 Notion, 개발 작업은 GitHub Issues와 PR에서 관리합니다.

## 참고 문서

- [파트 연결 구조](docs/architecture.md)
- [AI 모델 검토 양식](docs/model-review.md)
- [데이터셋 검토 양식](docs/dataset-review.md)
- [음성 데이터 보관 원칙](data/README.md)

**실제 음성, 개인정보, API 키, 모델 파일을 저장소에 올리지 않습니다.**
