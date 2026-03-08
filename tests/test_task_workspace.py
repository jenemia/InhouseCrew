from __future__ import annotations

import json
from pathlib import Path

import pytest

from inhouse_crew.task_workspace import TaskWorkspace, WorkspaceError


def test_task_workspace_creates_run_and_task_artifacts(tmp_path: Path) -> None:
    workspace = TaskWorkspace(tmp_path / "runs")

    run = workspace.create_run(
        crew_id="feature_delivery",
        input_summary="Implement custom llm",
        run_id="run-001",
    )
    task = workspace.create_task(
        run,
        task_id="plan_feature",
        input_markdown="# Input\n",
        metadata={"agent": "planner"},
    )
    result_path = workspace.write_task_result(
        task,
        result_markdown="# Result\n",
        metadata={"status": "completed"},
    )
    task_artifact_path = workspace.write_task_artifact(task, "failure.md", "# Failure\n")
    task_json_path = workspace.write_task_json_artifact(
        task,
        "failure.json",
        {"status": "failed"},
    )
    summary_path = workspace.write_run_summary(
        run,
        summary_markdown="# Summary\n",
        metadata={"run_status": "completed"},
    )
    run_artifact_path = workspace.write_run_artifact(run, "notes.md", "# Notes\n")
    run_json_path = workspace.write_run_json_artifact(
        run,
        "failure.json",
        {"status": "failed"},
    )

    assert run.run_dir == tmp_path / "runs" / "run-001"
    assert task.input_path.read_text(encoding="utf-8") == "# Input\n"
    task_status = json.loads(task.status_path.read_text(encoding="utf-8"))
    assert task_status["status"] == "pending"
    assert task_status["context_task_ids"] == []
    assert task_status["knowledge_reset_applied"] is None
    assert result_path.read_text(encoding="utf-8") == "# Result\n"
    assert task_artifact_path.read_text(encoding="utf-8") == "# Failure\n"
    assert json.loads(task_json_path.read_text(encoding="utf-8"))["status"] == "failed"
    assert summary_path.read_text(encoding="utf-8") == "# Summary\n"
    assert run_artifact_path.read_text(encoding="utf-8") == "# Notes\n"
    assert json.loads(run_json_path.read_text(encoding="utf-8"))["status"] == "failed"

    metadata = json.loads(task.metadata_path.read_text(encoding="utf-8"))
    assert metadata["agent"] == "planner"
    assert metadata["status"] == "completed"
    run_metadata = json.loads(run.metadata_path.read_text(encoding="utf-8"))
    assert run_metadata["run_status"] == "completed"


def test_task_workspace_surfaces_write_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = TaskWorkspace(tmp_path / "runs")
    run = workspace.create_run("feature_delivery", "summary", run_id="run-002")
    task = workspace.create_task(run, "review_feature", "# Input\n")

    def raise_os_error(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", raise_os_error)

    with pytest.raises(WorkspaceError, match="review_feature"):
        workspace.write_task_result(task, "# Result\n")
