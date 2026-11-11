"""Fake SDK only: never import the real SDK or use a microphone/API credential."""

import importlib
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ai import azure_pronunciation
from ai.pronunciation import AssessmentScores, AssessmentStatus


@pytest.fixture
def fake_sdk(synthetic_response):
    result = SimpleNamespace(
        reason="recognized",
        properties=SimpleNamespace(get_property=Mock(return_value=json.dumps(synthetic_response))),
    )
    recognizer = Mock()
    recognizer.recognize_once_async.return_value.get.return_value = result
    return SimpleNamespace(
        ResultReason=SimpleNamespace(
            RecognizedSpeech="recognized", NoMatch="no_match", Canceled="canceled"
        ),
        CancellationReason=SimpleNamespace(
            Error="error", EndOfStream="end_of_stream", CancelledByUser="cancelled_by_user"
        ),
        OutputFormat=SimpleNamespace(Detailed="detailed"),
        PropertyId=SimpleNamespace(SpeechServiceResponse_JsonResult="json_result"),
        SpeechConfig=Mock(),
        PronunciationAssessmentConfig=Mock(),
        PronunciationAssessmentGradingSystem=SimpleNamespace(HundredMark="hundred"),
        PronunciationAssessmentGranularity=SimpleNamespace(Word="word"),
        SpeechRecognizer=Mock(return_value=recognizer),
        fake_result=result,
    )


def test_sdk_result_uses_documented_json_property(fake_sdk):
    result = azure_pronunciation.assessment_from_sdk_result(
        fake_sdk.fake_result, speechsdk=fake_sdk
    )
    assert result.status == AssessmentStatus.SUCCESS
    assert result.scores.pronunciation == 81.5
    assert [(word.word, word.accuracy, word.error_type) for word in result.words] == [
        ("안녕하세요", 94.0, "None"),
        ("연습입니다", 51.0, "Mispronunciation"),
    ]
    fake_sdk.fake_result.properties.get_property.assert_called_once_with("json_result")


@pytest.mark.parametrize(
    ("reason", "status"),
    [
        ("no_match", AssessmentStatus.NO_MATCH),
        ("unknown", AssessmentStatus.RECOGNITION_FAILED),
    ],
)
def test_sdk_failure_never_reads_scores_or_raw_diagnostics(fake_sdk, reason, status):
    fake_sdk.fake_result.reason = reason
    result = azure_pronunciation.assessment_from_sdk_result(
        fake_sdk.fake_result, speechsdk=fake_sdk
    )
    assert result.status == status
    assert result.scores == AssessmentScores()
    fake_sdk.fake_result.properties.get_property.assert_not_called()


@pytest.mark.parametrize(
    ("cancellation", "expected"),
    [
        ("error", AssessmentStatus.SERVICE_ERROR),
        ("cancelled_by_user", AssessmentStatus.CANCELED),
        ("end_of_stream", AssessmentStatus.CANCELED),
        ("unknown", AssessmentStatus.RECOGNITION_FAILED),
    ],
)
def test_cancellation_reason_is_classified_without_reading_details(
    fake_sdk, cancellation, expected, capsys
):
    class FakeCancellationDetails:
        reason = cancellation

        @property
        def error_details(self):
            raise AssertionError("Raw service error details must never be read")

    fake_sdk.fake_result.reason = "canceled"
    fake_sdk.fake_result.cancellation_details = FakeCancellationDetails()
    result = azure_pronunciation.assessment_from_sdk_result(
        fake_sdk.fake_result, speechsdk=fake_sdk
    )
    assert result.status == expected
    assert result.scores == AssessmentScores()
    assert not result.words
    if cancellation == "error":
        assert result.issues == ("sdk_cancellation_error",)
    fake_sdk.fake_result.properties.get_property.assert_not_called()
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("details", [None, SimpleNamespace()])
def test_missing_cancellation_reason_is_uncertain_not_a_clean_cancellation(fake_sdk, details):
    fake_sdk.fake_result.reason = "canceled"
    fake_sdk.fake_result.cancellation_details = details
    result = azure_pronunciation.assessment_from_sdk_result(
        fake_sdk.fake_result, speechsdk=fake_sdk
    )
    assert result.status == AssessmentStatus.RECOGNITION_FAILED
    assert result.issues == ("sdk_cancellation_reason_unavailable",)


@pytest.mark.parametrize("code", ["AuthenticationFailure", "ConnectionFailure", "ServiceTimeout"])
def test_service_error_cancellations_are_not_reported_as_user_cancellations(fake_sdk, code, capsys):
    fake_sdk.fake_result.reason = "canceled"
    fake_sdk.fake_result.cancellation_details = SimpleNamespace(
        reason="error", error_code=code, error_details="synthetic-private-key"
    )
    result = azure_pronunciation.assessment_from_sdk_result(
        fake_sdk.fake_result, speechsdk=fake_sdk
    )
    assert result.status == AssessmentStatus.SERVICE_ERROR
    assert result.issues == ("sdk_cancellation_error",)
    assert "synthetic-private-key" not in repr(result)
    assert capsys.readouterr() == ("", "")


def test_cancellation_metadata_exception_is_sanitized(fake_sdk, capsys):
    class UnavailableCancellation:
        reason = "canceled"

        @property
        def cancellation_details(self):
            raise RuntimeError("synthetic-private-key")

    result = azure_pronunciation.assessment_from_sdk_result(
        UnavailableCancellation(), speechsdk=fake_sdk
    )
    assert result.status == AssessmentStatus.RECOGNITION_FAILED
    assert "synthetic-private-key" not in repr(result)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("NBest", None, AssessmentStatus.INVALID_RESPONSE),
        ("NBest", [], AssessmentStatus.INVALID_RESPONSE),
        ("Words", None, AssessmentStatus.PARTIAL),
        ("Words", {"Word": "invalid container"}, AssessmentStatus.PARTIAL),
    ],
)
def test_detailed_sdk_json_still_requires_nbest_and_word_containers(
    fake_sdk, synthetic_response, field, value, expected
):
    target = synthetic_response if field == "NBest" else synthetic_response["NBest"][0]
    target[field] = value
    fake_sdk.fake_result.properties.get_property.return_value = json.dumps(synthetic_response)
    result = azure_pronunciation.assessment_from_sdk_result(
        fake_sdk.fake_result, speechsdk=fake_sdk
    )
    assert result.status == expected
    assert not result.words
    if field == "Words":
        assert result.scores.pronunciation == 81.5


@pytest.mark.parametrize("payload", [None, "", "{invalid", "null"])
def test_sdk_missing_or_invalid_json_is_safe(fake_sdk, payload):
    fake_sdk.fake_result.properties.get_property.return_value = payload
    result = azure_pronunciation.assessment_from_sdk_result(
        fake_sdk.fake_result, speechsdk=fake_sdk
    )
    assert result.status == AssessmentStatus.INVALID_RESPONSE


def test_sdk_property_error_does_not_expose_diagnostics(fake_sdk):
    fake_sdk.fake_result.properties.get_property.side_effect = RuntimeError(
        "synthetic private detail"
    )
    result = azure_pronunciation.assessment_from_sdk_result(
        fake_sdk.fake_result, speechsdk=fake_sdk
    )
    assert result.status == AssessmentStatus.INVALID_RESPONSE
    assert "synthetic private detail" not in repr(result)


def test_explicit_call_sets_korean_word_assessment_and_converts_result(monkeypatch, fake_sdk):
    monkeypatch.setattr(azure_pronunciation, "_load_sdk", lambda: fake_sdk)
    audio = object()
    result = azure_pronunciation.assess_once(
        key="synthetic-not-a-key",
        region="synthetic-region",
        reference_text="연습",
        audio_config=audio,
    )
    assert result.status == AssessmentStatus.SUCCESS
    assert fake_sdk.SpeechConfig.return_value.speech_recognition_language == "ko-KR"
    assert fake_sdk.SpeechConfig.return_value.output_format == fake_sdk.OutputFormat.Detailed
    fake_sdk.PronunciationAssessmentConfig.assert_called_once_with(
        reference_text="연습", grading_system="hundred", granularity="word", enable_miscue=True
    )
    fake_sdk.SpeechRecognizer.assert_called_once_with(
        speech_config=fake_sdk.SpeechConfig.return_value, audio_config=audio
    )
    fake_sdk.PronunciationAssessmentConfig.return_value.apply_to.assert_called_once_with(
        fake_sdk.SpeechRecognizer.return_value
    )
    fake_sdk.SpeechRecognizer.return_value.recognize_once_async.assert_called_once_with()


@pytest.mark.parametrize("stage", ["configuration", "recognition"])
def test_sdk_exception_is_not_a_zero_score(monkeypatch, fake_sdk, stage):
    monkeypatch.setattr(azure_pronunciation, "_load_sdk", lambda: fake_sdk)
    error = RuntimeError("synthetic private service detail")
    if stage == "configuration":
        fake_sdk.SpeechConfig.side_effect = error
    else:
        fake_sdk.SpeechRecognizer.return_value.recognize_once_async.return_value.get.side_effect = (
            error
        )
    result = azure_pronunciation.assess_once(
        key="synthetic-not-a-key",
        region="synthetic-region",
        reference_text="연습",
        audio_config=object(),
    )
    assert result.status == AssessmentStatus.SERVICE_ERROR
    assert result.scores == AssessmentScores()
    assert "synthetic private service detail" not in repr(result)


@pytest.mark.parametrize(
    "override", [{"key": ""}, {"region": " "}, {"reference_text": None}, {"audio_config": None}]
)
def test_bad_configuration_is_rejected_before_loading_sdk(monkeypatch, override):
    load = Mock(side_effect=AssertionError("SDK must not load"))
    monkeypatch.setattr(azure_pronunciation, "_load_sdk", load)
    kwargs = dict(
        key="synthetic-not-a-key", region="synthetic", reference_text="연습", audio_config=object()
    )
    kwargs.update(override)
    with pytest.raises(ValueError):
        azure_pronunciation.assess_once(**kwargs)
    load.assert_not_called()


def test_module_imports_do_not_read_environment_or_load_sdk(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Import must not read credentials")

    monkeypatch.setattr(os, "getenv", blocked)
    importlib.reload(azure_pronunciation)
    # The autouse fixture rejects Azure/dotenv imports and network operations.
    importlib.import_module("ai.experiments.azure_pronunciation_smoke")


def test_manual_experiment_requires_opt_in_before_reading_environment(monkeypatch):
    smoke = importlib.import_module("ai.experiments.azure_pronunciation_smoke")
    monkeypatch.setattr(sys, "argv", ["azure_pronunciation_smoke"])
    monkeypatch.setattr(os, "getenv", Mock(side_effect=AssertionError("Must opt in first")))
    with pytest.raises(SystemExit) as exc:
        smoke.main()
    assert exc.value.code == 2
