"""Explicit, opt-in Azure SDK boundary for the short Korean reading experiment."""

from __future__ import annotations

from typing import Any

from ai.pronunciation import (
    AssessmentStatus,
    PronunciationAssessment,
    parse_pronunciation_response,
)


def assessment_from_sdk_result(result: Any, *, speechsdk: Any) -> PronunciationAssessment:
    """Adapt local SDK properties; never send a request or log raw details."""
    if result.reason == speechsdk.ResultReason.NoMatch:
        return PronunciationAssessment(AssessmentStatus.NO_MATCH)
    if result.reason == speechsdk.ResultReason.Canceled:
        return PronunciationAssessment(AssessmentStatus.CANCELED)
    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        return PronunciationAssessment(AssessmentStatus.RECOGNITION_FAILED)
    try:
        payload = result.properties.get_property(
            speechsdk.PropertyId.SpeechServiceResponse_JsonResult
        )
    except (RuntimeError, ValueError):
        return PronunciationAssessment(
            AssessmentStatus.INVALID_RESPONSE, issues=("sdk_result_unavailable",)
        )
    return parse_pronunciation_response(payload)


def _load_sdk() -> Any:
    import azure.cognitiveservices.speech as speechsdk

    return speechsdk


def assess_once(
    *, key: str, region: str, reference_text: str, audio_config: Any
) -> PronunciationAssessment:
    """Make one paid call only when explicitly invoked with credentials and audio.

    The caller chooses audio input. No .env loading, microphone default, storage,
    prosody/syllable assessment or local error inference is performed here.
    """
    if not all(isinstance(value, str) and value.strip() for value in (key, region, reference_text)):
        raise ValueError("key, region and reference_text must be nonempty strings")
    if audio_config is None:
        raise ValueError("audio_config must be explicitly supplied")
    speechsdk = _load_sdk()
    try:
        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_recognition_language = "ko-KR"
        assessment_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Word,
            enable_miscue=True,
        )
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )
        assessment_config.apply_to(recognizer)
        result = recognizer.recognize_once_async().get()
    except (RuntimeError, ValueError):
        # SDK errors can contain credentials, session IDs and service diagnostics.
        return PronunciationAssessment(AssessmentStatus.SERVICE_ERROR, issues=("sdk_call_failed",))
    return assessment_from_sdk_result(result, speechsdk=speechsdk)
