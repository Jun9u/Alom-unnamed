"""Offline conversion tests; synthetic fixtures do not validate Korean scoring."""

import copy
import json
from dataclasses import asdict

import pytest

from ai.pronunciation import (
    AssessmentScores,
    AssessmentStatus,
    parse_pronunciation_response,
)


@pytest.mark.parametrize("as_json", [False, True])
@pytest.mark.parametrize("recognition", ["Success", 0])
def test_documented_fields_are_converted(synthetic_response, as_json, recognition):
    synthetic_response["RecognitionStatus"] = recognition
    original = copy.deepcopy(synthetic_response)
    payload = json.dumps(synthetic_response) if as_json else synthetic_response
    result = parse_pronunciation_response(payload)
    assert result.status == AssessmentStatus.SUCCESS
    assert result.recognized_text == "안녕하세요 연습입니다."
    assert result.scores == AssessmentScores(81.5, 82.0, 76.0, 90.0)
    assert [(word.word, word.accuracy, word.error_type) for word in result.words] == [
        ("안녕하세요", 94.0, "None"),
        ("연습입니다", 51.0, "Mispronunciation"),
    ]
    assert not result.issues
    assert json.loads(json.dumps(asdict(result)))["status"] == "success"
    assert synthetic_response == original


@pytest.mark.parametrize(
    "payload", [None, [], 3, True, "", "{bad", "null", "[]", "42", '{"x": NaN}', b"{}"]
)
def test_bad_json_or_root_is_a_separate_state(payload):
    result = parse_pronunciation_response(payload)
    assert result.status == AssessmentStatus.INVALID_RESPONSE
    assert result.scores == AssessmentScores()
    assert result.words == ()


def test_overly_nested_json_fails_safely():
    result = parse_pronunciation_response("[" * 2000 + "]" * 2000)
    assert result.status == AssessmentStatus.INVALID_RESPONSE


@pytest.mark.parametrize("recognition", [None, False, True, 0.0, 1, "Unknown", [], {}])
def test_missing_or_unknown_recognition_status_is_not_success(synthetic_response, recognition):
    synthetic_response["RecognitionStatus"] = recognition
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.INVALID_RESPONSE
    assert result.scores == AssessmentScores()


@pytest.mark.parametrize(
    ("recognition", "expected"),
    [
        ("NoMatch", AssessmentStatus.NO_MATCH),
        ("InitialSilenceTimeout", AssessmentStatus.NO_MATCH),
        ("BabbleTimeout", AssessmentStatus.NO_MATCH),
        ("Canceled", AssessmentStatus.CANCELED),
        ("Error", AssessmentStatus.RECOGNITION_FAILED),
        ("EndOfDictation", AssessmentStatus.RECOGNITION_FAILED),
    ],
)
def test_failure_discards_even_stale_scores(synthetic_response, recognition, expected):
    synthetic_response["RecognitionStatus"] = recognition
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == expected
    assert result.scores == AssessmentScores()
    assert result.recognized_text is None
    assert not result.words


@pytest.mark.parametrize("nbest", [None, [], {}, [None], ["invalid"]])
def test_unusable_first_hypothesis_is_invalid(synthetic_response, nbest):
    synthetic_response["NBest"] = nbest
    assert (
        parse_pronunciation_response(synthetic_response).status == AssessmentStatus.INVALID_RESPONSE
    )


@pytest.mark.parametrize(
    "field", ["PronScore", "AccuracyScore", "FluencyScore", "CompletenessScore"]
)
@pytest.mark.parametrize("missing", [True, False])
def test_missing_and_null_scores_remain_unavailable(synthetic_response, field, missing):
    scores = synthetic_response["NBest"][0]["PronunciationAssessment"]
    if missing:
        del scores[field]
    else:
        scores[field] = None
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert list(asdict(result.scores).values()).count(None) == 1
    assert f"PronunciationAssessment.{field}" in result.issues


@pytest.mark.parametrize(
    "invalid", ["95", True, -1, 101, float("nan"), float("inf"), {}, [], 10**500]
)
def test_invalid_scores_are_not_coerced_or_clamped(synthetic_response, invalid):
    best = synthetic_response["NBest"][0]
    best["PronunciationAssessment"]["AccuracyScore"] = invalid
    best["Words"][0]["PronunciationAssessment"]["AccuracyScore"] = invalid
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert result.scores.accuracy is None
    assert result.words[0].accuracy is None
    assert result.scores.pronunciation == 81.5


@pytest.mark.parametrize("score", [0, 100])
def test_real_boundary_scores_are_retained(synthetic_response, score):
    best = synthetic_response["NBest"][0]
    best["PronunciationAssessment"]["AccuracyScore"] = score
    best["Words"][0]["PronunciationAssessment"]["AccuracyScore"] = score
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.SUCCESS
    assert result.scores.accuracy == score
    assert result.words[0].accuracy == score
    # Error labels are passed through, never inferred from accuracy thresholds.
    assert result.words[0].error_type == "None"


@pytest.mark.parametrize("invalid", [None, [], "invalid"])
def test_invalid_assessment_container_is_partial(synthetic_response, invalid):
    synthetic_response["NBest"][0]["PronunciationAssessment"] = invalid
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert result.scores == AssessmentScores()


@pytest.mark.parametrize("words", [None, [], {}, "invalid"])
def test_missing_word_results_do_not_discard_summary(synthetic_response, words):
    synthetic_response["NBest"][0]["Words"] = words
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert result.scores.pronunciation == 81.5
    assert not result.words


def test_invalid_word_entries_do_not_hide_valid_words(synthetic_response):
    synthetic_response["NBest"][0]["Words"].extend([None, {}, {"Word": 1}, {"Word": " "}])
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert len(result.words) == 2


@pytest.mark.parametrize("details", [None, [], {}, {"AccuracyScore": 20}, {"ErrorType": None}])
def test_word_assessment_missing_fields_are_not_no_error(synthetic_response, details):
    synthetic_response["NBest"][0]["Words"][0]["PronunciationAssessment"] = details
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert result.words[0].error_type is None


@pytest.mark.parametrize("error", ["Omission", "Insertion"])
def test_returned_miscue_label_does_not_require_a_fabricated_accuracy(synthetic_response, error):
    synthetic_response["NBest"][0]["Words"][0]["PronunciationAssessment"] = {"ErrorType": error}
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.SUCCESS
    assert result.words[0].error_type == error
    assert result.words[0].accuracy is None


def test_unknown_provider_error_is_preserved_and_flagged(synthetic_response):
    synthetic_response["NBest"][0]["Words"][0]["PronunciationAssessment"]["ErrorType"] = (
        "FutureError"
    )
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert result.words[0].error_type == "FutureError"
    assert "Words[0].ErrorType.unknown" in result.issues


def test_asr_confidence_and_other_hypotheses_do_not_become_scores(synthetic_response):
    best = synthetic_response["NBest"][0]
    other = copy.deepcopy(best)
    best["Confidence"] = 0.01
    other["Confidence"] = 1.0
    other["PronunciationAssessment"]["PronScore"] = 100
    synthetic_response["NBest"].append(other)
    del best["PronunciationAssessment"]["PronScore"]
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert result.scores.pronunciation is None


def test_optional_unsupported_features_are_not_required_or_exposed(synthetic_response):
    best = synthetic_response["NBest"][0]
    best["PronunciationAssessment"]["ProsodyScore"] = 100
    best["Words"][0]["Syllables"] = [{"Syllable": "invented"}]
    best["Words"][0]["Phonemes"] = [{"Phoneme": "invented"}]
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.SUCCESS
    assert set(asdict(result.scores)) == {"pronunciation", "accuracy", "fluency", "completeness"}


def test_text_fallback_and_unavailable_text(synthetic_response):
    synthetic_response["NBest"][0]["Display"] = None
    assert (
        parse_pronunciation_response(synthetic_response).recognized_text == "안녕하세요 연습입니다."
    )
    synthetic_response["DisplayText"] = None
    result = parse_pronunciation_response(synthetic_response)
    assert result.status == AssessmentStatus.PARTIAL
    assert result.recognized_text is None
