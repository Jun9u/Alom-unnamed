"""Synthetic data only. No captured Azure payloads, recordings or credentials."""

import builtins
import socket

import pytest


@pytest.fixture(autouse=True)
def forbid_live_services(monkeypatch):
    """Make accidental SDK imports and network requests fail in AI unit tests."""
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "azure" or name.startswith("azure.") or name == "dotenv":
            raise AssertionError("Live Azure SDK and dotenv are forbidden in unit tests")
        return original_import(name, *args, **kwargs)

    def blocked(*args, **kwargs):
        raise AssertionError("Network access is forbidden in AI unit tests")

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)


@pytest.fixture
def synthetic_response():
    """Invented test values using documented keys; NOT a real Korean API result."""
    return {
        "_fixture": "SYNTHETIC_NOT_AN_AZURE_CAPTURE",
        "RecognitionStatus": "Success",
        "DisplayText": "안녕하세요 연습입니다.",
        "NBest": [
            {
                "Confidence": 0.99,
                "Display": "안녕하세요 연습입니다.",
                "PronunciationAssessment": {
                    "PronScore": 81.5,
                    "AccuracyScore": 82,
                    "FluencyScore": 76,
                    "CompletenessScore": 90,
                },
                "Words": [
                    {
                        "Word": "안녕하세요",
                        "PronunciationAssessment": {"AccuracyScore": 94, "ErrorType": "None"},
                    },
                    {
                        "Word": "연습입니다",
                        "PronunciationAssessment": {
                            "AccuracyScore": 51,
                            "ErrorType": "Mispronunciation",
                        },
                    },
                ],
            }
        ],
    }
