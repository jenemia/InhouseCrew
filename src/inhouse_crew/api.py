from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict

from .crew_factory import CrewFactory
from .orders import OrderStatusRecord, create_order, read_order_status
from .task_workspace import TaskWorkspace


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    crew_id: str
    user_request: str


def create_app(
    *,
    project_root: Path,
    config_root: Path,
    settings_path: Path,
    env_file: Path | None,
) -> FastAPI:
    factory = CrewFactory.from_paths(
        config_root=config_root,
        settings_path=settings_path,
        project_root=project_root,
        env_file=env_file,
    )
    workspace = TaskWorkspace((project_root / factory.settings.workspace_root).resolve())
    workspace.root.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="Inhouse Crew Pickup API")
    app.state.factory = factory
    app.state.workspace = workspace

    @app.post("/orders", status_code=status.HTTP_202_ACCEPTED)
    def create_order_endpoint(payload: CreateOrderRequest) -> dict[str, object]:
        if payload.crew_id not in app.state.factory.crews:
            raise HTTPException(status_code=404, detail="Unknown crew_id")

        run, status_record = create_order(
            workspace=app.state.workspace,
            crew_id=payload.crew_id,
            user_request=payload.user_request,
        )
        return _build_order_response(
            order_id=status_record.order_id,
            summary_file=status_record.summary_file,
            status_record=status_record,
        )

    @app.get("/orders/{order_id}/status")
    def get_order_status(order_id: str) -> dict[str, object]:
        try:
            status_record = read_order_status(app.state.workspace.root, order_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail="Unknown order_id") from error
        return status_record.to_dict()

    @app.get("/pickup/{order_id}")
    def pickup_order(order_id: str) -> Response:
        try:
            status_record = read_order_status(app.state.workspace.root, order_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail="Unknown order_id") from error

        if status_record.status in {"queued", "running"}:
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "order_id": order_id,
                    "status": status_record.status,
                    "message": "아직 결과가 준비되지 않았습니다.",
                },
            )

        if status_record.status == "failed":
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "order_id": order_id,
                    "status": status_record.status,
                    "error_type": status_record.error_type,
                    "error_message": status_record.error_message,
                },
            )

        summary_path = Path(status_record.summary_file)
        if not summary_path.exists():
            raise HTTPException(status_code=500, detail="summary.md is missing")

        return Response(
            content=summary_path.read_text(encoding="utf-8"),
            media_type="text/markdown",
        )

    return app


def run_api_server(
    *,
    project_root: Path,
    config_root: Path,
    settings_path: Path,
    env_file: Path | None,
    host: str,
    port: int,
) -> None:
    import uvicorn

    app = create_app(
        project_root=project_root,
        config_root=config_root,
        settings_path=settings_path,
        env_file=env_file,
    )
    uvicorn.run(app, host=host, port=port)


def _build_order_response(
    order_id: str,
    summary_file: str,
    status_record: OrderStatusRecord,
) -> dict[str, object]:
    return {
        "order_id": order_id,
        "status": status_record.status,
        "status_url": f"/orders/{order_id}/status",
        "pickup_url": f"/pickup/{order_id}",
        "summary_file": summary_file,
        "requested_at": status_record.requested_at,
    }


__all__ = ["create_app", "run_api_server"]
