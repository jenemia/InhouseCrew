from __future__ import annotations

import json
from pathlib import Path

from inhouse_crew.orders import build_pending_task_statuses, build_request_slug, create_order
from inhouse_crew.persona_loader import load_registry
from inhouse_crew.task_workspace import TaskWorkspace


def test_create_order_creates_queued_status_and_request_file(tmp_path: Path) -> None:
    workspace = TaskWorkspace(tmp_path / "workspace" / "runs")
    workspace.root.mkdir(parents=True, exist_ok=True)
    repo_root = Path(__file__).resolve().parents[1]
    _, crews = load_registry(repo_root / "configs")

    run, status_record = create_order(
        workspace=workspace,
        crew_id="quickstart",
        user_request="로컬 codex 세션 계획을 요약해줘!",
        task_statuses=build_pending_task_statuses(crews["quickstart"].tasks),
        requested_at="2026-03-07T12:00:00+00:00",
    )

    assert run.run_id.startswith("T20260307-000001_")
    assert status_record.status == "queued"
    assert (run.run_dir / "request.md").exists()

    status_payload = json.loads((run.run_dir / "status.json").read_text(encoding="utf-8"))
    assert status_payload["order_id"] == run.run_id
    assert status_payload["status"] == "queued"
    assert status_payload["task_statuses"]["summarize_request"]["status"] == "pending"
    assert (
        status_payload["task_statuses"]["summarize_request"]["task_dir_name"] == "1.planner"
    )
    assert status_payload["task_statuses"]["summarize_request"]["context_task_ids"] == []


def test_build_request_slug_preserves_korean_and_removes_unsafe_chars() -> None:
    slug = build_request_slug("  한글 요청 / with spaces & symbols?!  ")

    assert slug == "한글-요청-with-spaces-symbol"
