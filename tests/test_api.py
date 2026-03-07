from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from inhouse_crew.api import create_app
from inhouse_crew.orders import OrderStatusRecord, write_order_status
from inhouse_crew.task_workspace import TaskWorkspace


def test_post_orders_creates_order_workspace_and_status(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    app = create_app(
        project_root=tmp_path,
        config_root=repo_root / "configs",
        settings_path=repo_root / "configs" / "settings.yaml",
        env_file=None,
    )
    client = TestClient(app)

    response = client.post(
        "/orders",
        json={"crew_id": "quickstart", "user_request": "API 주문을 접수해줘"},
    )

    assert response.status_code == 202
    payload = response.json()
    order_id = payload["order_id"]
    run_dir = tmp_path / "workspace" / "runs" / order_id

    assert payload["status"] == "queued"
    assert payload["status_url"] == f"/orders/{order_id}/status"
    assert payload["pickup_url"] == f"/pickup/{order_id}"
    assert (run_dir / "status.json").exists()
    assert (run_dir / "request.md").exists()


def test_pickup_returns_markdown_when_order_is_completed(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    app = create_app(
        project_root=tmp_path,
        config_root=repo_root / "configs",
        settings_path=repo_root / "configs" / "settings.yaml",
        env_file=None,
    )
    client = TestClient(app)
    workspace = TaskWorkspace(tmp_path / "workspace" / "runs")
    workspace.root.mkdir(parents=True, exist_ok=True)

    run = workspace.create_run(
        crew_id="quickstart",
        input_summary="완료된 주문",
        run_id="T20260307-000001_완료된-주문",
        metadata={"requested_at": "2026-03-07T12:00:00+00:00"},
    )
    workspace.write_run_artifact(run, "request.md", "# 원본 요청\n\n완료된 주문\n")
    summary_path = workspace.write_run_summary(run, "# 실행 요약\n\n완료됨\n")
    write_order_status(
        workspace,
        run,
        OrderStatusRecord(
            order_id=run.run_id,
            crew_id="quickstart",
            status="completed",
            user_request_preview="완료된 주문",
            requested_at="2026-03-07T12:00:00+00:00",
            started_at="2026-03-07T12:00:01+00:00",
            finished_at="2026-03-07T12:00:02+00:00",
            summary_file=str(summary_path),
        ),
    )

    response = client.get(f"/pickup/{run.run_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "완료됨" in response.text


def test_pickup_returns_accepted_json_when_order_is_not_ready(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    app = create_app(
        project_root=tmp_path,
        config_root=repo_root / "configs",
        settings_path=repo_root / "configs" / "settings.yaml",
        env_file=None,
    )
    client = TestClient(app)

    create_response = client.post(
        "/orders",
        json={"crew_id": "quickstart", "user_request": "아직 완료되지 않은 주문"},
    )
    order_id = create_response.json()["order_id"]

    response = client.get(f"/pickup/{order_id}")

    assert response.status_code == 202
    payload = response.json()
    assert payload["order_id"] == order_id
    assert payload["status"] == "queued"
