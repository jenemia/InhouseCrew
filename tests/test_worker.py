from __future__ import annotations

import json
from pathlib import Path

from inhouse_crew.orders import create_order
from inhouse_crew.task_workspace import TaskWorkspace
from inhouse_crew.worker import run_worker_once
from tests.fakes import FailingFactory, FakeFactory


def test_run_worker_once_processes_queued_order(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    workspace = TaskWorkspace(tmp_path / "workspace" / "runs")
    workspace.root.mkdir(parents=True, exist_ok=True)
    factory = FakeFactory(repo_root / "configs")

    run, _ = create_order(
        workspace=workspace,
        crew_id="quickstart",
        user_request="워커가 주문을 처리해줘",
        requested_at="2026-03-07T12:00:00+00:00",
    )

    processed_order_id = run_worker_once(
        factory=factory,
        workspace=workspace,
        project_root=tmp_path,
    )

    assert processed_order_id == run.run_id
    status_payload = json.loads((run.run_dir / "status.json").read_text(encoding="utf-8"))
    assert status_payload["status"] == "completed"
    assert (run.run_dir / "summary.md").exists()


def test_run_worker_once_marks_failed_order_when_crew_fails(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    workspace = TaskWorkspace(tmp_path / "workspace" / "runs")
    workspace.root.mkdir(parents=True, exist_ok=True)
    factory = FailingFactory(repo_root / "configs")

    run, _ = create_order(
        workspace=workspace,
        crew_id="quickstart",
        user_request="실패하는 주문",
        requested_at="2026-03-07T12:00:00+00:00",
    )

    processed_order_id = run_worker_once(
        factory=factory,
        workspace=workspace,
        project_root=tmp_path,
    )

    assert processed_order_id == run.run_id
    status_payload = json.loads((run.run_dir / "status.json").read_text(encoding="utf-8"))
    assert status_payload["status"] == "failed"
    assert (run.run_dir / "failure.json").exists()
