from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter


@dataclass(slots=True, frozen=True)
class CodexFailureDetails:
    reason: str
    command: list[str]
    cwd: str | None
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    output_text: str = ""
    timeout_seconds: int | None = None
    prompt_chars: int | None = None
    llm_started_at: str | None = None
    llm_finished_at: str | None = None
    llm_elapsed_seconds: float | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "reason": self.reason,
            "command": self.command,
            "cwd": self.cwd,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "output_text": self.output_text,
            "timeout_seconds": self.timeout_seconds,
            "prompt_chars": self.prompt_chars,
            "llm_started_at": self.llm_started_at,
            "llm_finished_at": self.llm_finished_at,
            "llm_elapsed_seconds": self.llm_elapsed_seconds,
        }
        return {key: value for key, value in payload.items() if value not in (None, "", [])}


class CodexExecutionError(RuntimeError):
    """Raised when Codex CLI fails to produce a valid response."""

    def __init__(self, message: str, *, details: CodexFailureDetails) -> None:
        super().__init__(message)
        self.details = details


class CodexTimeoutError(CodexExecutionError, TimeoutError):
    """Raised when Codex CLI times out."""


@dataclass(slots=True)
class CodexRunResult:
    output_text: str
    stdout: str
    stderr: str
    returncode: int
    command: list[str]
    prompt_chars: int
    llm_started_at: str
    llm_finished_at: str
    llm_elapsed_seconds: float


class CodexRunner:
    _NON_RETRYABLE_REASONS = {"command_not_found", "command_start_failed"}

    def __init__(
        self,
        codex_command: str = "codex",
        model: str | None = None,
        timeout_seconds: int = 120,
        retry_count: int = 1,
        workdir: Path | None = None,
    ) -> None:
        self.codex_command = codex_command
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.retry_count = max(retry_count, 0)
        self.workdir = workdir

    def run(self, prompt: str, cwd: Path | None = None) -> CodexRunResult:
        resolved_cwd = cwd or self.workdir
        executable = self._ensure_command_available(cwd=resolved_cwd)
        last_error: Exception | None = None

        # 재시도 정책은 runner 레이어에서만 처리하고, 상위 레이어는 단일 예외로 다룬다.
        for _ in range(self.retry_count + 1):
            try:
                return self._run_once(prompt=prompt, cwd=resolved_cwd, executable=executable)
            except CodexExecutionError as error:
                last_error = error
                if error.details.reason in self._NON_RETRYABLE_REASONS:
                    break

        assert last_error is not None
        raise last_error

    def _run_once(
        self,
        prompt: str,
        cwd: Path | None = None,
        executable: str | None = None,
    ) -> CodexRunResult:
        with TemporaryDirectory(prefix="inhouse-codex-") as temp_dir:
            output_path = Path(temp_dir) / "last-message.txt"
            command = self._build_command(
                output_path=output_path,
                executable=executable or self.codex_command,
            )
            cwd_text = str(cwd) if cwd is not None else None
            prompt_chars = len(prompt)
            llm_started_at = datetime.now(UTC).isoformat()
            llm_started_at_perf = perf_counter()

            try:
                completed = subprocess.run(
                    [*command, prompt],
                    cwd=cwd_text,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                llm_finished_at = datetime.now(UTC).isoformat()
                llm_elapsed_seconds = round(perf_counter() - llm_started_at_perf, 3)
                raise CodexTimeoutError(
                    f"Codex CLI timed out after {self.timeout_seconds} seconds",
                    details=CodexFailureDetails(
                        reason="timeout",
                        command=command,
                        cwd=cwd_text,
                        timeout_seconds=self.timeout_seconds,
                        prompt_chars=prompt_chars,
                        llm_started_at=llm_started_at,
                        llm_finished_at=llm_finished_at,
                        llm_elapsed_seconds=llm_elapsed_seconds,
                    ),
                ) from error
            except OSError as error:
                llm_finished_at = datetime.now(UTC).isoformat()
                llm_elapsed_seconds = round(perf_counter() - llm_started_at_perf, 3)
                raise CodexExecutionError(
                    f"Codex CLI failed to start: {error.strerror or str(error)}",
                    details=CodexFailureDetails(
                        reason="command_start_failed",
                        command=command,
                        cwd=cwd_text,
                        prompt_chars=prompt_chars,
                        llm_started_at=llm_started_at,
                        llm_finished_at=llm_finished_at,
                        llm_elapsed_seconds=llm_elapsed_seconds,
                    ),
                ) from error

            # Codex exec는 마지막 응답 파일을 가장 안정적으로 남기므로 stdout보다 우선한다.
            llm_finished_at = datetime.now(UTC).isoformat()
            llm_elapsed_seconds = round(perf_counter() - llm_started_at_perf, 3)
            output_text = (
                output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
            )
            if not output_text:
                output_text = completed.stdout.strip()

            if completed.returncode != 0:
                raise CodexExecutionError(
                    "Codex CLI failed with exit code "
                    f"{completed.returncode}: "
                    f"{completed.stderr.strip() or completed.stdout.strip()}",
                    details=CodexFailureDetails(
                        reason="nonzero_exit",
                        command=command,
                        cwd=cwd_text,
                        returncode=completed.returncode,
                        stdout=completed.stdout.strip(),
                        stderr=completed.stderr.strip(),
                        output_text=output_text,
                        prompt_chars=prompt_chars,
                        llm_started_at=llm_started_at,
                        llm_finished_at=llm_finished_at,
                        llm_elapsed_seconds=llm_elapsed_seconds,
                    ),
                )

            if not output_text:
                raise CodexExecutionError(
                    "Codex CLI completed without a final response",
                    details=CodexFailureDetails(
                        reason="empty_response",
                        command=command,
                        cwd=cwd_text,
                        returncode=completed.returncode,
                        stdout=completed.stdout.strip(),
                        stderr=completed.stderr.strip(),
                        prompt_chars=prompt_chars,
                        llm_started_at=llm_started_at,
                        llm_finished_at=llm_finished_at,
                        llm_elapsed_seconds=llm_elapsed_seconds,
                    ),
                )

            return CodexRunResult(
                output_text=output_text,
                stdout=completed.stdout,
                stderr=completed.stderr,
                returncode=completed.returncode,
                command=command,
                prompt_chars=prompt_chars,
                llm_started_at=llm_started_at,
                llm_finished_at=llm_finished_at,
                llm_elapsed_seconds=llm_elapsed_seconds,
            )

    def _ensure_command_available(self, cwd: Path | None) -> str:
        resolved = shutil.which(self.codex_command)
        if resolved is None:
            raise CodexExecutionError(
                f"Codex command not found: {self.codex_command}",
                details=CodexFailureDetails(
                    reason="command_not_found",
                    command=[self.codex_command],
                    cwd=str(cwd) if cwd is not None else None,
                ),
            )
        return resolved

    def _build_command(self, output_path: Path, executable: str) -> list[str]:
        # 비대화형 일회성 실행만 허용해 CrewAI 호출 경로를 예측 가능하게 유지한다.
        command = [
            executable,
            "exec",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--ephemeral",
            "--output-last-message",
            str(output_path),
        ]
        if self.model:
            command.extend(["--model", self.model])
        return command
