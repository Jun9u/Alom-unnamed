"""Manual paid smoke experiment. Importing this module performs no I/O."""

import argparse
import json
import os
from dataclasses import asdict

from ai.azure_pronunciation import assess_once


def main() -> int:
    parser = argparse.ArgumentParser(description="한국어 발음평가 수동 실험 (유료 API)")
    parser.add_argument("--call-azure", action="store_true", help="실제 음성 전송 및 유료 호출")
    parser.add_argument(
        "--reference-text", default="안녕하세요. 저는 한국어 발음을 연습하고 있습니다."
    )
    args = parser.parse_args()
    if not args.call_azure:
        parser.error("실제 호출에는 --call-azure가 필요합니다.")
    key = os.getenv("SPEECH_KEY")
    region = os.getenv("SPEECH_REGION")
    if not key or not region:
        parser.error(
            "현재 프로세스에 SPEECH_KEY와 SPEECH_REGION을 설정하세요. .env는 읽지 않습니다."
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
