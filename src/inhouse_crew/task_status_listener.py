from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from crewai.events import (
    BaseEventListener,
    TaskCompletedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
)
from crewai.events.event_bus import CrewAIEventsBus

from .orders import TaskStatusRecord, read_order_status, write_order_status
from .task_workspace import RunContext, TaskContext, TaskWorkspace, WorkspaceError


class CrewTaskStatusListener(BaseEventListener):
    def __init__(
        self,
        *,
        workspace: TaskWorkspace,
        run: RunContext,
        task_contexts: dict[str, TaskContext],
        initial_task_statuses: dict[str, TaskStatusRecord],
        log_fn: Callable[[str], None] | None = None,
    ) -> None:
        self.workspace = workspace
        self.run = run
        self.task_contexts = task_contexts
        self.initial_task_statuses = initial_task_statuses
        self.log_fn = log_fn
        self._lock = Lock()
        super().__init__()

    def setup_listeners(self, crewai_event_bus: CrewAIEventsBus) -> None:
        @crewai_event_bus.on(TaskStartedEvent)
        def handle_task_started(_: Any, event: TaskStartedEvent) -> None:
            task_id = self._resolve_task_id(event.task)
            if task_id is None:
                return
            with self._lock:
                current = self._read_current_task_status(task_id)
                started_at = current.started_at or datetime.now(UTC).isoformat()
                updated = replace(current, status="running", started_at=started_at)
                self._write_task_status(updated)
                self._log(
                    f"[task] run_id={self.run.run_id} task={task_id} "
                    f"agent={current.agent} status=running"
                )

        @crewai_event_bus.on(TaskCompletedEvent)
        def handle_task_completed(_: Any, event: TaskCompletedEvent) -> None:
            task_id = self._resolve_task_id(event.task, event.output)
            if task_id is None:
                return
            with self._lock:
                current = self._read_current_task_status(task_id)
                task_context = self.task_contexts[task_id]
                result_path = self._persist_task_result(task_context, event.output)
                artifact_path = self._persist_output_artifact(
                    task_context,
                    current.output_artifact,
                    result_path,
                )
                finished_at = datetime.now(UTC).isoformat()
                telemetry = self._read_task_telemetry(event.task)
                updated = replace(
                    current,
                    status="done",
                    started_at=current.started_at or finished_at,
                    finished_at=finished_at,
                    result_file=str(result_path),
                    output_artifact=(
                        str(artifact_path) if artifact_path else current.output_artifact
                    ),
                    prompt_chars=telemetry["prompt_chars"],
                    llm_started_at=telemetry["llm_started_at"],
                    llm_finished_at=telemetry["llm_finished_at"],
                    llm_elapsed_seconds=telemetry["llm_elapsed_seconds"],
                )
                self._write_task_status(updated)
                self._log(
                    f"[task] run_id={self.run.run_id} task={task_id} "
                    f"agent={current.agent} status=done"
                )

        @crewai_event_bus.on(TaskFailedEvent)
        def handle_task_failed(_: Any, event: TaskFailedEvent) -> None:
            task_id = self._resolve_task_id(event.task)
            if task_id is None:
                return
            with self._lock:
                current = self._read_current_task_status(task_id)
                task_context = self.task_contexts[task_id]
                finished_at = datetime.now(UTC).isoformat()
                telemetry = self._read_task_telemetry(event.task)
                updated = replace(
                    current,
                    status="failed",
                    started_at=current.started_at or finished_at,
                    finished_at=finished_at,
                    failure_file=str(task_context.task_dir / "failure.json"),
                    prompt_chars=telemetry["prompt_chars"],
                    llm_started_at=telemetry["llm_started_at"],
                    llm_finished_at=telemetry["llm_finished_at"],
                    llm_elapsed_seconds=telemetry["llm_elapsed_seconds"],
                )
                self._write_task_status(updated)
                self._log(
                    f"[task] run_id={self.run.run_id} task={task_id} "
                    f"agent={current.agent} status=failed error={event.error}"
                )

    def _resolve_task_id(self, task: Any | None, output: Any | None = None) -> str | None:
        for candidate in (
            getattr(task, "name", None),
            getattr(output, "name", None),
        ):
            if isinstance(candidate, str) and candidate in self.task_contexts:
                return candidate
        return None

    def _read_current_task_status(self, task_id: str) -> TaskStatusRecord:
        order_status = read_order_status(self.workspace.root, self.run.run_id)
        return order_status.task_statuses.get(task_id, self.initial_task_statuses[task_id])

    def _write_task_status(self, task_status: TaskStatusRecord) -> None:
        task_context = self.task_contexts[task_status.task_id]
        self.workspace.write_task_status(task_context, task_status.to_dict())
        order_status = read_order_status(self.workspace.root, self.run.run_id)
        updated_task_statuses = dict(order_status.task_statuses)
        updated_task_statuses[task_status.task_id] = task_status
        updated_order_status = replace(order_status, task_statuses=updated_task_statuses)
        write_order_status(self.workspace, self.run, updated_order_status)

    def _persist_task_result(self, task: TaskContext, output: Any) -> Path:
        result_markdown = _task_output_to_markdown(task.task_id, output)
        try:
            return self.workspace.write_task_result(
                task,
                result_markdown=result_markdown,
                metadata={"status": "completed"},
            )
        except WorkspaceError:
            return task.result_path

    def _persist_output_artifact(
        self,
        task: TaskContext,
        output_artifact: str | None,
        result_path: Path,
    ) -> Path | None:
        if output_artifact is None:
            return None
        try:
            content = result_path.read_text(encoding="utf-8")
            return self.workspace.write_task_artifact(task, Path(output_artifact).name, content)
        except OSError:
            return None

    def _log(self, message: str) -> None:
        if self.log_fn is not None:
            self.log_fn(message)

    def _read_task_telemetry(self, task: Any | None) -> dict[str, int | float | str | None]:
        telemetry = getattr(task, "_inhouse_llm_telemetry", None)
        if not isinstance(telemetry, dict):
            return {
                "prompt_chars": None,
                "llm_started_at": None,
                "llm_finished_at": None,
                "llm_elapsed_seconds": None,
            }
        return {
            "prompt_chars": telemetry.get("prompt_chars")
            if isinstance(telemetry.get("prompt_chars"), int)
            else None,
            "llm_started_at": telemetry.get("llm_started_at")
            if isinstance(telemetry.get("llm_started_at"), str)
            else None,
            "llm_finished_at": telemetry.get("llm_finished_at")
            if isinstance(telemetry.get("llm_finished_at"), str)
            else None,
            "llm_elapsed_seconds": float(telemetry.get("llm_elapsed_seconds"))
            if isinstance(telemetry.get("llm_elapsed_seconds"), int | float)
            else None,
        }


def _task_output_to_markdown(task_id: str, output: object | None) -> str:
    if output is None:
        return f"# {task_id}\n\n_출력이 기록되지 않았습니다._\n"

    raw_output = getattr(output, "raw", None)
    body = str(raw_output if raw_output else output).strip()
    if not body:
        body = "_출력이 기록되지 않았습니다._"
    return f"# {task_id}\n\n{body}\n"


__all__ = ["CrewTaskStatusListener"]
