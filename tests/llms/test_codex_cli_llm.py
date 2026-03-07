from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from inhouse_crew.llms.codex_cli_llm import CodexCliLLM
from inhouse_crew.llms.codex_runner import (
    CodexExecutionError,
    CodexRunner,
    CodexTimeoutError,
)


def test_codex_runner_returns_output_file_content(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: list[str],
        cwd: str | None,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text("runner output\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="stdout output\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda command: f"/usr/bin/{command}")
    runner = CodexRunner(timeout_seconds=15, retry_count=0)

    result = runner.run("say hello")

    assert result.output_text == "runner output"
    assert result.returncode == 0
    assert result.command[0] == "/usr/bin/codex"


def test_codex_runner_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: list[str],
        cwd: str | None,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda command: f"/usr/bin/{command}")
    runner = CodexRunner(retry_count=0)

    with pytest.raises(CodexExecutionError, match="exit code 1") as exc_info:
        runner.run("fail")

    assert exc_info.value.details.reason == "nonzero_exit"
    assert exc_info.value.details.returncode == 1
    assert exc_info.value.details.stderr == "boom"


def test_codex_runner_raises_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: list[str],
        cwd: str | None,
        capture_output: bool,
        text: bool,
        timeout: int,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda command: f"/usr/bin/{command}")
    runner = CodexRunner(timeout_seconds=5, retry_count=0)

    with pytest.raises(CodexTimeoutError, match="5 seconds") as exc_info:
        runner.run("timeout")

    assert exc_info.value.details.reason == "timeout"
    assert exc_info.value.details.timeout_seconds == 5


def test_codex_runner_raises_before_retry_when_command_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess.run should not be called when codex is missing")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(shutil, "which", lambda command: None)
    runner = CodexRunner(retry_count=3)

    with pytest.raises(CodexExecutionError, match="Codex command not found") as exc_info:
        runner.run("fail fast")

    assert exc_info.value.details.reason == "command_not_found"
    assert exc_info.value.details.command == ["codex"]


def test_codex_cli_llm_formats_messages_for_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_run(prompt: str, cwd: Path | None = None):  # type: ignore[no-untyped-def]
        captured["prompt"] = prompt
        return type("Result", (), {"output_text": "done"})()

    llm = CodexCliLLM(retry_count=0)
    monkeypatch.setattr(llm.runner, "run", fake_run)

    result = llm.call(
        [
            {"role": "system", "content": "system rule"},
            {"role": "user", "content": "implement feature"},
        ]
    )

    assert result == "done"
    assert "SYSTEM:\nsystem rule" in captured["prompt"]
    assert "USER:\nimplement feature" in captured["prompt"]


def test_codex_cli_llm_reports_no_function_calling() -> None:
    llm = CodexCliLLM(retry_count=0)

    assert llm.supports_function_calling() is False
