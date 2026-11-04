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
    fake_sdk.fake_result.properties.get_property.assert_called_once_with("json_result")


@pytest.mark.parametrize(
    ("reason", "status"),
    [
        ("no_match", AssessmentStatus.NO_MATCH),
        ("canceled", AssessmentStatus.CANCELED),
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
