"""Test setup safeguards only; these tests do not validate a speech model."""

import pytest

from scripts.check_repo_hygiene import MAX_BYTES, inspect_file


@pytest.mark.parametrize("path", [".env", ".env.local", "backend/.env.production"])
def test_environment_files_are_rejected(path):
    assert "environment file" in inspect_file(path, b"SPEECH_KEY=example")


@pytest.mark.parametrize("path", [".env.example", ".env.template", "backend/.env.example"])
def test_empty_templates_are_allowed(path):
    assert inspect_file(path, b"SPEECH_KEY=\n") == []


@pytest.mark.parametrize("path", ["voice.wav", "voice.WAV", "model.safetensors", "weights.pt"])
def test_recordings_and_weights_are_rejected(path):
    assert "recording or model file" in inspect_file(path, b"sample")


def test_data_readme_is_allowed():
    assert inspect_file("data/README.md", b"Data policy") == []


def test_other_data_files_are_rejected():
    assert "local data directory" in inspect_file("data/labels.json", b"{}")


def test_large_file_is_rejected():
    assert "file larger than 5 MiB" in inspect_file("sample.bin", b"0" * (MAX_BYTES + 1))


def test_token_is_rejected_without_a_real_token():
    fake_token = b"ghp_" + b"a" * 36
    assert "possible credential or private key" in inspect_file("config.py", fake_token)


def test_private_key_header_is_rejected():
    fake_header = b"-----BEGIN " + b"RSA PRIVATE KEY-----"
    assert "possible credential or private key" in inspect_file("key.txt", fake_header)


def test_normal_source_is_allowed():
    assert inspect_file("ai/example.py", b"print('hello')\n") == []
