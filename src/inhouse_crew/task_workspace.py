from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


class WorkspaceError(RuntimeError):
    """Raised when workspace artifacts cannot be written."""


@dataclass(slots=True)
class RunContext:
    run_id: str
    crew_id: str
    started_at: str
    run_dir: Path
    metadata_path: Path
    summary_path: Path


@dataclass(slots=True)
class TaskContext:
    task_id: str
    task_dir: Path
    input_path: Path
    result_path: Path
    metadata_path: Path


class TaskWorkspace:
    def __init__(self, root: Path) -> None:
        self.root = root

    def create_run(
        self,
        crew_id: str,
        input_summary: str,
        run_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> RunContext:
        started_at = datetime.now(UTC).isoformat()
        resolved_run_id = run_id or self._build_run_id(crew_id)
        run_dir = self.root / resolved_run_id
        metadata_path = run_dir / "run-metadata.json"
        summary_path = run_dir / "summary.md"

        try:
            # run 디렉터리는 한 번만 생성해, 같은 run_id 중복 사용을 바로 드러낸다.
            run_dir.mkdir(parents=True, exist_ok=False)
            self._write_json(
                metadata_path,
                {
                    "run_id": resolved_run_id,
                    "crew_id": crew_id,
                    "started_at": started_at,
                    "input_summary": input_summary,
                    **(metadata or {}),
                },
            )
        except OSError as error:
            raise WorkspaceError(f"Failed to create run workspace at {run_dir}") from error

        return RunContext(
            run_id=resolved_run_id,
            crew_id=crew_id,
            started_at=started_at,
            run_dir=run_dir,
            metadata_path=metadata_path,
            summary_path=summary_path,
        )

    def create_task(
        self,
        run: RunContext,
        task_id: str,
        input_markdown: str,
        metadata: dict[str, object] | None = None,
    ) -> TaskContext:
        task_dir = run.run_dir / task_id
        input_path = task_dir / "input.md"
        result_path = task_dir / "result.md"
        metadata_path = task_dir / "metadata.json"

        try:
            # 각 task는 입력/결과/메타데이터를 같은 폴더에 저장해 추적 가능성을 높인다.
            task_dir.mkdir(parents=True, exist_ok=False)
            input_path.write_text(input_markdown, encoding="utf-8")
            self._write_json(
                metadata_path,
                {
                    "task_id": task_id,
                    "run_id": run.run_id,
                    **(metadata or {}),
                },
            )
        except OSError as error:
            raise WorkspaceError(f"Failed to create task workspace for {task_id}") from error

        return TaskContext(
            task_id=task_id,
            task_dir=task_dir,
            input_path=input_path,
            result_path=result_path,
            metadata_path=metadata_path,
        )

    def write_task_result(
        self,
        task: TaskContext,
        result_markdown: str,
        metadata: dict[str, object] | None = None,
    ) -> Path:
        try:
            self._write_text(task.result_path, result_markdown)
            if metadata:
                # 실행 중 갱신되는 상태값은 metadata.json에 누적해서 남긴다.
                current_metadata = json.loads(task.metadata_path.read_text(encoding="utf-8"))
                current_metadata.update(metadata)
                self._write_json(task.metadata_path, current_metadata)
        except OSError as error:
            raise WorkspaceError(f"Failed to write task result for {task.task_id}") from error

        return task.result_path

    def write_run_summary(
        self,
        run: RunContext,
        summary_markdown: str,
        metadata: dict[str, object] | None = None,
    ) -> Path:
        try:
            self._write_text(run.summary_path, summary_markdown)
            if metadata:
                current_metadata = json.loads(run.metadata_path.read_text(encoding="utf-8"))
                current_metadata.update(metadata)
                self._write_json(run.metadata_path, current_metadata)
        except OSError as error:
            raise WorkspaceError(f"Failed to write run summary for {run.run_id}") from error

        return run.summary_path

    def write_task_artifact(self, task: TaskContext, artifact_name: str, content: str) -> Path:
        artifact_path = task.task_dir / artifact_name
        try:
            self._write_text(artifact_path, content)
        except OSError as error:
            raise WorkspaceError(
                f"Failed to write task artifact '{artifact_name}' for {task.task_id}"
            ) from error
        return artifact_path

    def write_task_json_artifact(
        self,
        task: TaskContext,
        artifact_name: str,
        payload: dict[str, object],
    ) -> Path:
        artifact_path = task.task_dir / artifact_name
        try:
            self._write_json(artifact_path, payload)
        except OSError as error:
            raise WorkspaceError(
                f"Failed to write task artifact '{artifact_name}' for {task.task_id}"
            ) from error
        return artifact_path

    def write_run_artifact(self, run: RunContext, artifact_name: str, content: str) -> Path:
        artifact_path = run.run_dir / artifact_name
        try:
            self._write_text(artifact_path, content)
        except OSError as error:
            raise WorkspaceError(
                f"Failed to write run artifact '{artifact_name}' for {run.run_id}"
            ) from error
        return artifact_path

    def write_run_json_artifact(
        self,
        run: RunContext,
        artifact_name: str,
        payload: dict[str, object],
    ) -> Path:
        artifact_path = run.run_dir / artifact_name
        try:
            self._write_json(artifact_path, payload)
        except OSError as error:
            raise WorkspaceError(
                f"Failed to write run artifact '{artifact_name}' for {run.run_id}"
            ) from error
        return artifact_path

    def _build_run_id(self, crew_id: str) -> str:
        # run_id에 시각과 crew id를 같이 넣어 사람이 폴더만 보고도 맥락을 알 수 있게 한다.
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        suffix = uuid4().hex[:8]
        return f"{timestamp}-{crew_id}-{suffix}"

    def _write_text(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")

    def _write_json(self, path: Path, payload: dict[str, object]) -> None:
        # JSON은 정렬/개행을 고정해 diff와 수동 검토가 쉽도록 저장한다.
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
