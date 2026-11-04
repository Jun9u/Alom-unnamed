# AI

한국어 음성 분석의 실제 출력과 한계를 작은 실험으로 검증합니다.

기술 스택과 첫 구현 범위는 팀에서 결정합니다. Azure 연동은 검증용 실험이며 최종 모델 선정이 아닙니다.

## Azure 발음평가 실험

- `pronunciation.py`: SDK나 외부 연결 없이 JSON을 불변 dataclass로 변환합니다.
- `azure_pronunciation.py`: 명시적으로 호출할 때만 SDK 요청을 수행하고 결과를 변환기에 전달합니다.
- `experiments/azure_pronunciation_smoke.py`: 나중에 마이크로 실행하는 수동 실험입니다.
- `tests/`: 실제 Azure 응답을 수집하지 않고 만든 가상 데이터로 검증합니다.

이 데이터 구조는 AI 내부 실험용입니다. 프론트·백엔드 공통 API 명세, 저장 정책,
권한·예산은 확정하지 않습니다. 연결 전 관련 담당자의 입출력·실패 처리 검토가 필요합니다.

## 설치와 오프라인 테스트

저장소 루트의 기존 가상환경을 사용합니다. 저장소 CI 기준은 Python 3.11이며,
이번 로컬 환경은 Python 3.13.2, 수동 실험 SDK 고정 버전은 1.53.0입니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest ai/tests
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

결과 변환은 Python 표준 라이브러리만 사용합니다. 단위 테스트에 Azure SDK,
`.env`, API 키, 녹음 파일이 필요하지 않습니다. AI 테스트에서는 실제 SDK import와
네트워크 연결을 차단하며, 일반 CI에는 유료 API 호출을 추가하지 않습니다.

## 결과 구조와 실패 처리

```python
from dataclasses import asdict
from ai.pronunciation import parse_pronunciation_response

# API 호출 없이 동작하는 가상 실패 응답 예시입니다.
result = parse_pronunciation_response('{"RecognitionStatus": "NoMatch"}')
assert result.status == "no_match"
assert result.scores.pronunciation is None
structured = asdict(result)
```

| 필드 | 의미 |
|---|---|
| `status` | `success`, `partial`, `invalid_response`, `no_match`, `canceled`, `recognition_failed`, `service_error` |
| `recognized_text` | 인식 문자열 또는 `None`. 발음 정확도의 근거로 재계산하지 않음 |
| `scores.pronunciation` | Azure `PronScore` 종합 점수 |
| `scores.accuracy`, `fluency`, `completeness` | 정확도, 유창성, 완성도 |
| `words` | 단어 문자열, 정확도, Azure가 반환한 오류 유형의 튜플 |
| `issues` | 누락·잘못된 필드 경로 또는 실패 코드. 원시 응답·예외 내용은 넣지 않음 |

HundredMark 기준 0~100의 유한 숫자만 받습니다. 유효한 0점은 유지하지만,
누락·null·문자열·불리언·범위 밖 점수는 `None`으로 두고 `partial`로 표시합니다.
잘못된 JSON·최상위 구조·첫 `NBest`는 `invalid_response`로 처리합니다.
`RecognitionStatus`가 없거나 알 수 없으면 성공으로 간주하지 않습니다.
성공 표기 `"Success"`와 공식 JSON 예시의 정수 `0`을 지원합니다.
인식 실패·취소 시 점수와 단어를 비우며, 실패를 발음 0점으로 바꾸지 않습니다.

첫 `NBest`만 사용하며 ASR `Confidence`를 점수로 변환하거나 다른 후보의 점수를
섞지 않습니다. 종합 점수도 평균 등으로 재계산하지 않습니다.
단어 오류는 반환된 `None`(오류 없음), `Mispronunciation`, `Omission`, `Insertion`을
그대로 옮기고, 없는 오류 유형은 Python `None`으로 구별합니다.
알 수 없는 오류 문자열은 보존하되 `partial` 및 `issues`로 표시합니다.
누락·삽입 단어에 정확도가 없으면 점수를 만들어 넣지 않습니다.

## 나중에 실행할 실제 음성 실험

아래 실행은 실제 음성 전송과 유료 호출을 포함합니다. 현재 마이크가 없어 실행하지 않습니다.
짧은 한국어 예문을 한 번 읽는 scripted 평가에 한정합니다.
30초 초과·연속 인식·다중 구간 점수 합산은 구현하지 않았습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r ai/requirements-azure.txt
# 승인된 방법으로 현재 프로세스에 SPEECH_KEY, SPEECH_REGION을 주입한 후 실행합니다.
.\.venv\Scripts\python.exe -m ai.experiments.azure_pronunciation_smoke --call-azure
```

스크립트는 `.env`를 읽지 않습니다. import 및 `--help`는 API나 마이크를 사용하지 않습니다.
실제 호출에는 `--call-azure`가 필요하며, 인식 문자열·단어를 포함하는 구조화 결과는
로컬 콘솔에만 표시합니다. 실제 결과·콘솔 출력·녹음·키를 커밋하거나 업로드하지 않습니다.
기존 SDK 호출부는 한국어 `ko-KR`, `HundredMark`, `Word`, `enable_miscue=True`를 사용합니다.
단어 오류 유형은 제공자가 반환한 경우에만 노출하며 텍스트 비교로 추정하지 않습니다.
한국어 운율 평가, 음절 평가, 음소별 진단을 추가하거나 지원한다고 가정하지 않습니다.
가상 데이터 테스트는 한국어 응답의 실제 필드 제공 여부, 모델 성능, 임상적 타당성을
검증하지 않습니다. 실제 음성 검증과 사람의 검토가 남아 있습니다.

근거: [Azure 발음평가 설정·결과 필드](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment?pivots=programming-language-python),
[지원 언어](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=pronunciation-assessment).
공식 문서에서 운율 평가는 en-US, 음절별 정확도도 en-US로 제한하므로 이 실험에서는 사용하지 않습니다.
