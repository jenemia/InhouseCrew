from __future__ import annotations

import json
from pathlib import Path

from inhouse_crew.orders import build_pending_task_statuses, create_order
from inhouse_crew.task_workspace import TaskWorkspace
from inhouse_crew.worker import run_worker_once
from tests.fakes import FailingFactory, FakeFactory


def test_run_worker_once_processes_queued_order(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    workspace = TaskWorkspace(tmp_path / "workspace" / "runs")
    workspace.root.mkdir(parents=True, exist_ok=True)
    factory = FakeFactory(repo_root / "configs")

    run, _ = create_order(
        workspace=workspace,
        crew_id="quickstart",
        user_request="워커가 주문을 처리해줘",
        task_statuses=build_pending_task_statuses(factory.crews["quickstart"].tasks),
        requested_at="2026-03-07T12:00:00+00:00",
    )

    processed_order_id = run_worker_once(
        factory=factory,
        workspace=workspace,
        project_root=tmp_path,
    )
    captured = capsys.readouterr()

    assert processed_order_id == run.run_id
    status_payload = json.loads((run.run_dir / "status.json").read_text(encoding="utf-8"))
    assert status_payload["status"] == "completed"
    assert status_payload["task_statuses"]["summarize_request"]["status"] == "done"
    assert status_payload["task_statuses"]["summarize_request"]["task_dir_name"] == "1.planner"
    assert (run.run_dir / "summary.md").exists()
    assert (run.run_dir / "1.planner" / "status.json").exists()
    assert f"picked order_id={run.run_id}" in captured.out
    assert f"[task] run_id={run.run_id} task=summarize_request" in captured.out
    assert f"completed order_id={run.run_id}" in captured.out


def test_run_worker_once_marks_failed_order_when_crew_fails(
    tmp_path: Path,
    monkeypatch,
    capsys,
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
        task_statuses=build_pending_task_statuses(factory.crews["quickstart"].tasks),
        requested_at="2026-03-07T12:00:00+00:00",
    )

    processed_order_id = run_worker_once(
        factory=factory,
        workspace=workspace,
        project_root=tmp_path,
    )
    captured = capsys.readouterr()

    assert processed_order_id == run.run_id
    status_payload = json.loads((run.run_dir / "status.json").read_text(encoding="utf-8"))
    assert status_payload["status"] == "failed"
    assert status_payload["task_statuses"]["summarize_request"]["status"] == "failed"
    assert status_payload["task_statuses"]["summarize_request"]["task_dir_name"] == "1.planner"
    assert (run.run_dir / "failure.json").exists()
    assert f"picked order_id={run.run_id}" in captured.out
    assert "status=failed" in captured.out
    assert f"failed order_id={run.run_id}" in captured.out
