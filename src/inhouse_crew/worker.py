from __future__ import annotations

import time
from pathlib import Path

from .crew_factory import CrewFactory
from .main import CrewRunExecutionError, run_crew
from .orders import (
    claim_order,
    list_queued_order_ids,
    load_order_run,
    read_request_markdown,
    release_claim,
)
from .task_workspace import TaskWorkspace


def run_worker_loop(
    *,
    project_root: Path,
    config_root: Path,
    settings_path: Path,
    env_file: Path | None,
    once: bool,
    poll_interval: float,
) -> int:
    factory = CrewFactory.from_paths(
        config_root=config_root,
        settings_path=settings_path,
        project_root=project_root,
        env_file=env_file,
    )
    workspace = TaskWorkspace((project_root / factory.settings.workspace_root).resolve())
    workspace.root.mkdir(parents=True, exist_ok=True)

    while True:
        processed = run_worker_once(
            factory=factory,
            workspace=workspace,
            project_root=project_root,
        )
        if once:
            return 0
        if not processed:
            time.sleep(poll_interval)


def run_worker_once(
    *,
    factory: CrewFactory,
    workspace: TaskWorkspace,
    project_root: Path,
) -> str | None:
    for order_id in list_queued_order_ids(workspace.root):
        run = load_order_run(workspace, order_id)
        claim_path = claim_order(run.run_dir)
        if claim_path is None:
            continue

        try:
            user_request = read_request_markdown(run)
            run_crew(
                factory=factory,
                crew_id=run.crew_id,
                user_request=user_request,
                project_root=project_root,
                run_id=order_id,
            )
        except CrewRunExecutionError:
            return order_id
        finally:
            release_claim(claim_path)

        return order_id

    return None


__all__ = ["run_worker_loop", "run_worker_once"]
