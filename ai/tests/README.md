# AI 테스트

`conftest.py`의 `synthetic_response`는 문서의 키를 참고해 직접 만든 **가상 응답**입니다.
실제 Azure 한국어 응답 캡처나 실측 점수가 아니며, 한국어에서 각 필드가 항상
제공됨을 보장하지 않습니다. 녹음·개인정보·실제 API 키는 포함하지 않습니다.

`test_pronunciation.py`는 점수·단어 변환, 누락·null·잘못된 JSON·유효하지 않은 값,
인식 실패와 부분 결과를 검사합니다. `test_azure_pronunciation.py`는 가짜 SDK로
상세 출력 설정·취소/서비스 오류 구분·단어 결과 연결·import 시 부작용 방지를 검사합니다.
`test_smoke_credentials.py`는 가짜 dotenv 파서와 가상 프로세스 환경으로 명시적
동의 전 설정 접근 차단, 환경변수 우선순위, 변수 치환 금지, 설정 오류의 상세정보
비노출을 검사합니다. 실제 `.env`나 실제 프로세스 키를 사용하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m pytest ai/tests
```

실제 SDK import와 네트워크 연결을 차단합니다. 실제 음성 API 호출은 일반 CI에
넣지 않습니다. 통과는 모델 정확도나 임상적 타당성 검증을 의미하지 않습니다.
