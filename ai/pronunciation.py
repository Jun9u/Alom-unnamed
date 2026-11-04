"""Convert Azure HundredMark scripted assessment JSON without SDK or I/O."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum


class AssessmentStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    INVALID_RESPONSE = "invalid_response"
    NO_MATCH = "no_match"
    CANCELED = "canceled"
    RECOGNITION_FAILED = "recognition_failed"
    SERVICE_ERROR = "service_error"


@dataclass(frozen=True)
class AssessmentScores:
    pronunciation: float | None = None
    accuracy: float | None = None
    fluency: float | None = None
    completeness: float | None = None


@dataclass(frozen=True)
class WordAssessment:
    word: str
    accuracy: float | None
    # Azure's literal "None" means no reported error; Python None means unavailable.
    error_type: str | None


@dataclass(frozen=True)
class PronunciationAssessment:
    status: AssessmentStatus
    recognized_text: str | None = None
    scores: AssessmentScores = field(default_factory=AssessmentScores)
    words: tuple[WordAssessment, ...] = ()
    # Field paths/reason codes only; never include raw response or exception details.
    issues: tuple[str, ...] = ()


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _score(value: object) -> float | None:
    # Do not coerce strings, booleans, nonfinite numbers or out-of-range values.
    if type(value) in (int, float) and 0 <= value <= 100:
        return float(value)
    return None


def _reject_constant(value: str) -> None:
    raise ValueError("Nonstandard JSON number")


def parse_pronunciation_response(payload: object) -> PronunciationAssessment:
    """Read the first NBest hypothesis; never derive scores from ASR confidence.

    Accept a JSON string or decoded dict. Missing/invalid evaluation fields produce
    a partial result with None values, never fabricated zeros. This experimental
    data model is not the frontend/backend API contract.
    """
    if isinstance(payload, str):
        try:
            payload = json.loads(payload, parse_constant=_reject_constant)
        except (ValueError, RecursionError):
            return PronunciationAssessment(
                AssessmentStatus.INVALID_RESPONSE, issues=("invalid_json",)
            )
    if not isinstance(payload, dict):
        return PronunciationAssessment(
            AssessmentStatus.INVALID_RESPONSE, issues=("response_object_required",)
        )

    recognition = payload.get("RecognitionStatus")
    success = recognition == "Success" or (type(recognition) is int and recognition == 0)
    if not success:
        if isinstance(recognition, str) and recognition in {
            "NoMatch",
            "InitialSilenceTimeout",
            "BabbleTimeout",
        }:
            status = AssessmentStatus.NO_MATCH
        elif recognition == "Canceled":
            status = AssessmentStatus.CANCELED
        elif isinstance(recognition, str) and recognition in {"Error", "EndOfDictation"}:
            status = AssessmentStatus.RECOGNITION_FAILED
        else:
            status = AssessmentStatus.INVALID_RESPONSE
        return PronunciationAssessment(status, issues=("RecognitionStatus",))

    nbest = payload.get("NBest")
    if not isinstance(nbest, list) or not nbest or not isinstance(nbest[0], dict):
        return PronunciationAssessment(AssessmentStatus.INVALID_RESPONSE, issues=("NBest[0]",))
    best = nbest[0]
    issues: list[str] = []
    text = _text(best.get("Display")) or _text(payload.get("DisplayText"))
    if text is None:
        issues.append("DisplayText")
    assessment = best.get("PronunciationAssessment")
    if not isinstance(assessment, dict):
        issues.append("PronunciationAssessment")
        assessment = {}
    scores = {}
    for target, source in (
        ("pronunciation", "PronScore"),
        ("accuracy", "AccuracyScore"),
        ("fluency", "FluencyScore"),
        ("completeness", "CompletenessScore"),
    ):
        scores[target] = _score(assessment.get(source))
        if scores[target] is None:
            issues.append(f"PronunciationAssessment.{source}")

    raw_words = best.get("Words")
    words: list[WordAssessment] = []
    if not isinstance(raw_words, list) or not raw_words:
        issues.append("Words")
        raw_words = []
    for index, raw in enumerate(raw_words):
        path = f"Words[{index}]"
        if not isinstance(raw, dict) or _text(raw.get("Word")) is None:
            issues.append(path)
            continue
        details = raw.get("PronunciationAssessment")
        if not isinstance(details, dict):
            issues.append(f"{path}.PronunciationAssessment")
            details = {}
        error = _text(details.get("ErrorType"))
        if error is None:
            issues.append(f"{path}.ErrorType")
        elif error not in {"None", "Omission", "Insertion", "Mispronunciation"}:
            # Preserve unknown provider values without claiming locale support.
            issues.append(f"{path}.ErrorType.unknown")
        accuracy = _score(details.get("AccuracyScore"))
        if accuracy is None and not (
            details.get("AccuracyScore") is None and error in {"Omission", "Insertion"}
        ):
            issues.append(f"{path}.AccuracyScore")
        words.append(WordAssessment(raw["Word"], accuracy, error))

    return PronunciationAssessment(
        status=AssessmentStatus.PARTIAL if issues else AssessmentStatus.SUCCESS,
        recognized_text=text,
        scores=AssessmentScores(**scores),
        words=tuple(words),
        issues=tuple(issues),
    )
