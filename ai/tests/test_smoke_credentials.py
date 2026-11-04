"""Exercise optional .env settings using a fake parser, never the real .env."""

import builtins
import importlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ai.experiments import azure_pronunciation_smoke as smoke


@pytest.fixture(autouse=True)
def isolate_credential_environment(monkeypatch):
    """Ensure no real process credential is ever used by these tests."""
    monkeypatch.setattr(os, "environ", {})


@pytest.fixture
def fake_dotenv(monkeypatch):
    """Intercept only the optional dotenv import; the real library stays blocked."""
    read = Mock(return_value={"SPEECH_KEY": "synthetic-not-a-key", "SPEECH_REGION": "synthetic"})
    guarded_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "dotenv":
            return SimpleNamespace(dotenv_values=read)
        return guarded_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    return read


def test_env_file_is_opt_in_and_process_values_work_without_dotenv(monkeypatch):
    monkeypatch.setenv("SPEECH_KEY", "synthetic-process-key")
    monkeypatch.setenv("SPEECH_REGION", "synthetic-process-region")
    # The autouse guard would fail any real dotenv import or file parsing.
    assert smoke._load_credentials(use_dotenv=False) == (
        "synthetic-process-key",
        "synthetic-process-region",
    )


def test_opt_in_uses_only_repo_env_without_interpolation_or_environment_mutation(fake_dotenv):
    before = dict(os.environ)
    assert smoke._load_credentials(use_dotenv=True) == ("synthetic-not-a-key", "synthetic")
    fake_dotenv.assert_called_once_with(
        dotenv_path=Path(smoke.__file__).resolve().parents[2] / ".env",
        interpolate=False,
        encoding="utf-8-sig",
    )
    assert dict(os.environ) == before


def test_process_values_override_file_values(monkeypatch, fake_dotenv):
    monkeypatch.setenv("SPEECH_KEY", "synthetic-process-key")
    monkeypatch.setenv("SPEECH_REGION", "synthetic-process-region")
    assert smoke._load_credentials(use_dotenv=True) == (
        "synthetic-process-key",
        "synthetic-process-region",
    )


def test_file_fills_only_the_missing_process_value(monkeypatch, fake_dotenv):
    monkeypatch.setenv("SPEECH_KEY", "synthetic-process-key")
    assert smoke._load_credentials(use_dotenv=True) == ("synthetic-process-key", "synthetic")


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"SPEECH_KEY": None, "SPEECH_REGION": "synthetic"},
        {"SPEECH_KEY": "synthetic", "SPEECH_REGION": " "},
    ],
)
def test_missing_or_blank_file_values_fail_without_exposing_values(fake_dotenv, values):
    fake_dotenv.return_value = values
    with pytest.raises(ValueError, match="^Speech credentials are missing$"):
        smoke._load_credentials(use_dotenv=True)


def test_empty_process_value_does_not_silently_use_stale_file_key(monkeypatch, fake_dotenv):
    monkeypatch.setenv("SPEECH_KEY", "")
    with pytest.raises(ValueError):
        smoke._load_credentials(use_dotenv=True)


@pytest.mark.parametrize("args", [[], ["--use-dotenv"]])
def test_env_reader_is_never_called_without_call_azure(monkeypatch, args, capsys):
    monkeypatch.setattr(sys, "argv", ["smoke", *args])
    load = Mock(side_effect=AssertionError("No opt-in"))
    monkeypatch.setattr(smoke, "_load_credentials", load)
    with pytest.raises(SystemExit) as exc:
        smoke.main()
    assert exc.value.code == 2
    load.assert_not_called()
    assert "--call-azure" in capsys.readouterr().err


@pytest.mark.parametrize("args", [["--help"], ["--use-dotenv", "--help"]])
def test_help_does_not_read_credentials_or_import_sdk(monkeypatch, args):
    monkeypatch.setattr(sys, "argv", ["smoke", *args])
    load = Mock(side_effect=AssertionError("Help must not load credentials"))
    monkeypatch.setattr(smoke, "_load_credentials", load)
    with pytest.raises(SystemExit) as exc:
        smoke.main()
    assert exc.value.code == 0
    load.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        OSError("synthetic-private-key"),
        UnicodeError("synthetic-private-key"),
        ValueError("synthetic-private-key"),
        ImportError("synthetic-private-key"),
    ],
)
def test_credential_load_errors_stop_before_sdk_without_private_details(monkeypatch, error, capsys):
    monkeypatch.setattr(sys, "argv", ["smoke", "--call-azure", "--use-dotenv"])
    monkeypatch.setattr(smoke, "_load_credentials", Mock(side_effect=error))
    with pytest.raises(SystemExit) as exc:
        smoke.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert "synthetic-private-key" not in captured.err


def test_actual_opt_in_loader_errors_are_sanitized(monkeypatch, fake_dotenv, capsys):
    monkeypatch.setattr(sys, "argv", ["smoke", "--call-azure", "--use-dotenv"])
    fake_dotenv.side_effect = PermissionError("synthetic-private-key")
    with pytest.raises(SystemExit) as exc:
        smoke.main()
    assert exc.value.code == 2
    assert "synthetic-private-key" not in capsys.readouterr().err


def test_import_does_not_read_file_environment_or_optional_dependencies(monkeypatch):
    monkeypatch.setattr(
        os, "getenv", Mock(side_effect=AssertionError("No import-time credentials"))
    )
    # Real SDK/dotenv imports remain blocked by the autouse fixture.
    importlib.reload(smoke)
