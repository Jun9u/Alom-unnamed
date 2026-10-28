"""Run the guard against a temporary Git index, never against a real account."""

import subprocess
import sys
from pathlib import Path

CHECKER = Path(__file__).resolve().parents[1] / "scripts" / "check_repo_hygiene.py"


def run_git(folder: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=folder, check=True, capture_output=True)


def run_checker(folder: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECKER)], cwd=folder, capture_output=True, text=True, check=False
    )


def test_clean_index_passes(tmp_path):
    run_git(tmp_path, "init")
    (tmp_path / "hello.py").write_text("print('hello')\n", encoding="utf-8")
    run_git(tmp_path, "add", "hello.py")
    result = run_checker(tmp_path)
    assert result.returncode == 0


def test_staged_secret_is_found_even_when_working_copy_is_clean(tmp_path):
    run_git(tmp_path, "init")
    fake_token = "ghp_" + "b" * 36
    target = tmp_path / "settings.py"
    target.write_text(f"TOKEN = '{fake_token}'\n", encoding="utf-8")
    run_git(tmp_path, "add", "settings.py")
    target.write_text("TOKEN = ''\n", encoding="utf-8")
    result = run_checker(tmp_path)
    assert result.returncode == 1
    assert "settings.py" in result.stderr
    assert fake_token not in result.stderr
    assert fake_token not in result.stdout


def test_running_outside_repository_fails_clearly(tmp_path):
    result = run_checker(tmp_path)
    assert result.returncode == 2
    assert "Git index" in result.stderr
