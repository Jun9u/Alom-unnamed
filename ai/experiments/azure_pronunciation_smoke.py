"""Manual paid smoke experiment. Importing this module performs no I/O."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from ai.azure_pronunciation import assess_once


def _load_credentials(*, use_dotenv: bool) -> tuple[str, str]:
    """Read optional repo .env without interpolation or modifying the environment."""
    values = {}
    if use_dotenv:
        from dotenv import dotenv_values

        values = dotenv_values(
            dotenv_path=Path(__file__).resolve().parents[2] / ".env",
            interpolate=False,
            encoding="utf-8-sig",
        )
    # An explicitly supplied process variable takes precedence, even when empty.
    key = os.getenv("SPEECH_KEY", values.get("SPEECH_KEY"))
    region = os.getenv("SPEECH_REGION", values.get("SPEECH_REGION"))
    if not all(isinstance(value, str) and value.strip() for value in (key, region)):
        raise ValueError("Speech credentials are missing")
    return key.strip(), region.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="한국어 발음평가 수동 실험 (유료 API)")
    parser.add_argument("--call-azure", action="store_true", help="실제 음성 전송 및 유료 호출")
    parser.add_argument(
        "--use-dotenv", action="store_true", help="저장소 루트의 .env에서 키·리전을 선택적으로 읽기"
    )
    parser.add_argument(
        "--reference-text", default="안녕하세요. 저는 한국어 발음을 연습하고 있습니다."
    )
    args = parser.parse_args()
    if not args.call_azure:
        parser.error("실제 호출에는 --call-azure가 필요합니다.")
    try:
        key, region = _load_credentials(use_dotenv=args.use_dotenv)
    except ImportError:
        parser.error(".env 사용에는 ai/requirements-azure.txt의 선택적 의존성을 설치하세요.")
    except (OSError, UnicodeError, ValueError):
        parser.error(
            "SPEECH_KEY와 SPEECH_REGION을 프로세스 환경변수 또는 --use-dotenv 설정에서 확인하세요."
        )

    import azure.cognitiveservices.speech as speechsdk

    print("다음 문장을 읽어주세요:")
    print(args.reference_text)
    assessment = assess_once(
        key=key,
        region=region,
        reference_text=args.reference_text,
        audio_config=speechsdk.audio.AudioConfig(use_default_microphone=True),
    )
    print(json.dumps(asdict(assessment), ensure_ascii=False, indent=2))
    return 0 if assessment.status.value == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
