from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from .task_workspace import RunContext, TaskWorkspace, WorkspaceError

OrderStatusValue = Literal["queued", "running", "completed", "failed"]

_ORDER_ID_PATTERN = re.compile(r"^T(?P<date>\d{8})-(?P<sequence>\d{6})(?:_.+)?$")


@dataclass(slots=True, frozen=True)
class OrderStatusRecord:
    order_id: str
    crew_id: str
    status: OrderStatusValue
    user_request_preview: str
    requested_at: str
    summary_file: str
    started_at: str | None = None
    finished_at: str | None = None
    failure_file: str | None = None
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "order_id": self.order_id,
            "crew_id": self.crew_id,
            "status": self.status,
            "user_request_preview": self.user_request_preview,
            "requested_at": self.requested_at,
            "summary_file": self.summary_file,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "failure_file": self.failure_file,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "OrderStatusRecord":
        return cls(
            order_id=str(payload["order_id"]),
            crew_id=str(payload["crew_id"]),
            status=str(payload["status"]),  # type: ignore[arg-type]
            user_request_preview=str(payload["user_request_preview"]),
            requested_at=str(payload["requested_at"]),
            summary_file=str(payload["summary_file"]),
            started_at=_get_optional_str(payload, "started_at"),
            finished_at=_get_optional_str(payload, "finished_at"),
            failure_file=_get_optional_str(payload, "failure_file"),
            error_type=_get_optional_str(payload, "error_type"),
            error_message=_get_optional_str(payload, "error_message"),
        )


def create_order(
    workspace: TaskWorkspace,
    crew_id: str,
    user_request: str,
    requested_at: str | None = None,
) -> tuple[RunContext, OrderStatusRecord]:
    requested_at_value = requested_at or datetime.now(UTC).isoformat()
    requested_at_dt = datetime.fromisoformat(requested_at_value)
    slug = build_request_slug(user_request)
    next_sequence = _next_order_sequence(workspace.root, requested_at_dt)

    while True:
        order_id = build_order_id(requested_at_dt, next_sequence, slug)
        try:
            run = workspace.create_run(
                crew_id=crew_id,
                input_summary=build_user_request_preview(user_request),
                run_id=order_id,
                metadata={"requested_at": requested_at_value, "status": "queued"},
            )
            break
        except WorkspaceError:
            next_sequence += 1

    workspace.write_run_artifact(run, "request.md", build_request_markdown(user_request))
    status = OrderStatusRecord(
        order_id=run.run_id,
        crew_id=crew_id,
        status="queued",
        user_request_preview=build_user_request_preview(user_request),
        requested_at=requested_at_value,
        summary_file=str(run.summary_path),
    )
    write_order_status(workspace, run, status)
    return run, status


def build_order_id(requested_at: datetime, sequence: int, slug: str) -> str:
    prefix = f"T{requested_at.strftime('%Y%m%d')}-{sequence:06d}"
    return f"{prefix}_{slug}"


def build_request_slug(user_request: str, max_length: int = 24) -> str:
    normalized = re.sub(r"\s+", "-", user_request.strip())
    normalized = re.sub(r"[^0-9A-Za-z가-힣_-]+", "", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-_")
    if not normalized:
        return "요청"
    return normalized[:max_length].rstrip("-_") or "요청"


def build_user_request_preview(user_request: str, max_length: int = 120) -> str:
    compact = re.sub(r"\s+", " ", user_request.strip())
    if len(compact) <= max_length:
        return compact
    return compact[: max_length - 1].rstrip() + "…"


def build_request_markdown(user_request: str) -> str:
    return f"# 원본 요청\n\n{user_request.strip()}\n"


def read_request_markdown(run: RunContext) -> str:
    request_path = run.run_dir / "request.md"
    content = request_path.read_text(encoding="utf-8").strip()
    if content.startswith("# 원본 요청"):
        _, _, body = content.partition("\n\n")
        return body.strip()
    return content


def write_order_status(
    workspace: TaskWorkspace,
    run: RunContext,
    status: OrderStatusRecord,
) -> Path:
    return workspace.write_run_json_artifact(run, "status.json", status.to_dict())


def read_order_status(workspace_root: Path, order_id: str) -> OrderStatusRecord:
    status_path = workspace_root / order_id / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid status.json for order '{order_id}'")
    return OrderStatusRecord.from_dict(payload)


def load_order_run(workspace: TaskWorkspace, order_id: str) -> RunContext:
    run_dir = workspace.root / order_id
    metadata_path = run_dir / "run-metadata.json"
    summary_path = run_dir / "summary.md"
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise WorkspaceError(f"Failed to load existing run workspace at {run_dir}") from error

    return RunContext(
        run_id=order_id,
        crew_id=str(payload["crew_id"]),
        started_at=str(payload["started_at"]),
        run_dir=run_dir,
        metadata_path=metadata_path,
        summary_path=summary_path,
    )


def list_queued_order_ids(workspace_root: Path) -> list[str]:
    order_ids: list[str] = []
    for status_path in sorted(workspace_root.glob("*/status.json")):
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("status") == "queued":
            order_ids.append(str(payload.get("order_id") or status_path.parent.name))
    return order_ids


def claim_order(run_dir: Path) -> Path | None:
    claim_path = run_dir / ".worker.claim"
    try:
        with claim_path.open("x", encoding="utf-8") as file:
            file.write(f"{os.getpid()}\n")
    except FileExistsError:
        return None
    return claim_path


def release_claim(claim_path: Path | None) -> None:
    if claim_path is None:
        return
    try:
        claim_path.unlink()
    except FileNotFoundError:
        return


def _next_order_sequence(workspace_root: Path, requested_at: datetime) -> int:
    date_part = requested_at.strftime("%Y%m%d")
    highest = 0
    for run_dir in workspace_root.glob(f"T{date_part}-*"):
        match = _ORDER_ID_PATTERN.match(run_dir.name)
        if match and match.group("date") == date_part:
            highest = max(highest, int(match.group("sequence")))
    return highest + 1


def _get_optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return None if value in (None, "") else str(value)


__all__ = [
    "OrderStatusRecord",
    "OrderStatusValue",
    "build_order_id",
    "build_request_markdown",
    "build_request_slug",
    "build_user_request_preview",
    "claim_order",
    "create_order",
    "list_queued_order_ids",
    "load_order_run",
    "read_order_status",
    "read_request_markdown",
    "release_claim",
    "write_order_status",
]
