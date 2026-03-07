from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from .crew_factory import CrewFactory, CrewFactoryError
from .llms import CodexExecutionError
from .orders import (
    OrderStatusRecord,
    build_request_markdown,
    build_user_request_preview,
    load_order_run,
    write_order_status,
)
from .persona_loader import CrewTaskSpec
from .task_workspace import RunContext, TaskContext, TaskWorkspace, WorkspaceError


class CrewRunExecutionError(RuntimeError):
    """Raised when a crew run fails after workspace bootstrap."""

    def __init__(self, message: str, *, run_dir: Path, summary_path: Path | None = None) -> None:
        super().__init__(message)
        self.run_dir = run_dir
        self.summary_path = summary_path


def build_parser() -> argparse.ArgumentParser:
    # 현재 엔트리포인트는 단일 실행 경로만 제공하고, 나머지 책임은 팩토리/워크스페이스로 넘긴다.
    parser = argparse.ArgumentParser(description="Run Inhouse Crew workflows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a configured crew.")
    _add_runtime_options(run_parser)
    run_parser.add_argument("--crew-id", default="quickstart", help="Crew ID from configs/crews.")
    input_group = run_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", help="Inline user request text.")
    input_group.add_argument("--input-file", help="Path to a text/Markdown input file.")

    api_parser = subparsers.add_parser("api", help="Serve order intake and pickup HTTP APIs.")
    _add_runtime_options(api_parser)
    api_parser.add_argument("--host", default="127.0.0.1", help="Host for the HTTP server.")
    api_parser.add_argument("--port", type=int, default=8000, help="Port for the HTTP server.")

    worker_parser = subparsers.add_parser("worker", help="Process queued orders from workspace.")
    _add_runtime_options(worker_parser)
    worker_parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one queued order and then exit.",
    )
    worker_parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds when no queued order exists.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            summary_path = run_from_args(args)
        except CrewRunExecutionError as error:
            print(str(error), file=sys.stderr)
            return 1
        print(summary_path)
        return 0
    if args.command == "api":
        run_api_from_args(args)
        return 0
    if args.command == "worker":
        return run_worker_from_args(args)

    parser.error(f"Unsupported command: {args.command}")
    return 2


def _add_runtime_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config-root", default="configs", help="Config directory path.")
    parser.add_argument(
        "--settings-path",
        default="configs/settings.yaml",
        help="Settings YAML path.",
    )
    parser.add_argument("--env-file", default=".env", help="Optional env file path.")


def _resolve_runtime_paths(args: argparse.Namespace, project_root: Path) -> tuple[Path, Path, Path]:
    config_root = project_root / args.config_root
    settings_path = project_root / args.settings_path
    env_file = project_root / args.env_file
    return config_root, settings_path, env_file


def run_from_args(args: argparse.Namespace) -> Path:
    project_root = Path.cwd()
    config_root, settings_path, env_file = _resolve_runtime_paths(args, project_root)
    user_request = _read_user_request(args, project_root)

    # 설정 로딩과 Crew 조립 책임은 CLI가 아니라 팩토리에 집중시킨다.
    factory = CrewFactory.from_paths(
        config_root=config_root,
        settings_path=settings_path,
        project_root=project_root,
        env_file=env_file if env_file.exists() else None,
    )
    return run_crew(
        factory=factory,
        crew_id=args.crew_id,
        user_request=user_request,
        project_root=project_root,
    )


def run_api_from_args(args: argparse.Namespace) -> None:
    from .api import run_api_server

    project_root = Path.cwd()
    config_root, settings_path, env_file = _resolve_runtime_paths(args, project_root)
    run_api_server(
        project_root=project_root,
        config_root=config_root,
        settings_path=settings_path,
        env_file=env_file if env_file.exists() else None,
        host=args.host,
        port=args.port,
    )


def run_worker_from_args(args: argparse.Namespace) -> int:
    from .worker import run_worker_loop

    project_root = Path.cwd()
    config_root, settings_path, env_file = _resolve_runtime_paths(args, project_root)
    return run_worker_loop(
        project_root=project_root,
        config_root=config_root,
        settings_path=settings_path,
        env_file=env_file if env_file.exists() else None,
        once=args.once,
        poll_interval=args.poll_interval,
    )


def run_crew(
    factory: CrewFactory,
    crew_id: str,
    user_request: str,
    project_root: Path,
    run_id: str | None = None,
    requested_at: str | None = None,
) -> Path:
    try:
        spec = factory.crews[crew_id]
    except KeyError as error:
        raise CrewFactoryError(f"Unknown crew '{crew_id}'") from error

    workspace = TaskWorkspace((project_root / factory.settings.workspace_root).resolve())
    workspace.root.mkdir(parents=True, exist_ok=True)
    run = _resolve_run_context(
        workspace=workspace,
        crew_id=crew_id,
        user_request=user_request,
        run_id=run_id,
        requested_at=requested_at,
    )
    _ensure_run_request_artifact(workspace=workspace, run=run, user_request=user_request)
    requested_at_value = _resolve_requested_at(run=run, requested_at=requested_at)
    started_at_value = datetime.now(UTC).isoformat()
    _write_run_status(
        workspace=workspace,
        run=run,
        status="running",
        crew_id=crew_id,
        user_request=user_request,
        requested_at=requested_at_value,
        started_at=started_at_value,
    )

    crew = None
    task_contexts: dict[str, TaskContext] = {}

    try:
        task_contexts = {
            task_spec.id: workspace.create_task(
                run,
                task_id=task_spec.id,
                input_markdown=_build_task_input_markdown(
                    task_spec.id,
                    task_spec.description,
                    user_request,
                ),
                metadata={
                    "agent": task_spec.agent,
                    "expected_output": task_spec.expected_output,
                    "output_artifact": task_spec.output_artifact,
                },
            )
            for task_spec in spec.tasks
        }

        # 실제 task 실행은 CrewAI에 맡기고, 결과 저장 정책만 프로젝트 레이어에서 관리한다.
        crew = factory.create_crew(crew_id)
        result = crew.kickoff(
            inputs={
                "user_request": user_request,
                "current_date": datetime.now(UTC).date().isoformat(),
            }
        )

        last_result_path = run.summary_path
        for crew_task, task_spec in zip(crew.tasks, spec.tasks, strict=True):
            task_context = task_contexts[task_spec.id]
            last_result_path = workspace.write_task_result(
                task_context,
                result_markdown=_task_output_to_markdown(task_spec.id, crew_task.output),
                metadata={"status": "completed"},
            )

        summary_markdown = _build_run_summary(
            crew_id=crew_id,
            user_request=user_request,
            result=result,
        )
        summary_path = workspace.write_run_summary(
            run,
            summary_markdown=summary_markdown,
            metadata={"status": "completed", "final_result_path": str(last_result_path)},
        )
        _write_run_status(
            workspace=workspace,
            run=run,
            status="completed",
            crew_id=crew_id,
            user_request=user_request,
            requested_at=requested_at_value,
            started_at=started_at_value,
            finished_at=datetime.now(UTC).isoformat(),
        )
        return summary_path
    except Exception as error:
        failure_summary_path: Path | None = None
        persistence_error: WorkspaceError | None = None
        try:
            failure_summary_path = _persist_run_failure(
                workspace=workspace,
                run=run,
                task_contexts=task_contexts,
                spec_tasks=spec.tasks,
                crew=crew,
                crew_id=crew_id,
                user_request=user_request,
                error=error,
            )
        except WorkspaceError as workspace_error:
            persistence_error = workspace_error

        _write_run_status(
            workspace=workspace,
            run=run,
            status="failed",
            crew_id=crew_id,
            user_request=user_request,
            requested_at=requested_at_value,
            started_at=started_at_value,
            finished_at=datetime.now(UTC).isoformat(),
            failure_file=str(run.run_dir / "failure.json"),
            error_type=type(error).__name__,
            error_message=str(error),
        )

        raise CrewRunExecutionError(
            _build_cli_failure_message(
                crew_id=crew_id,
                run=run,
                failure_summary_path=failure_summary_path,
                error=error,
                persistence_error=persistence_error,
            ),
            run_dir=run.run_dir,
            summary_path=failure_summary_path,
        ) from error


def _resolve_run_context(
    workspace: TaskWorkspace,
    crew_id: str,
    user_request: str,
    run_id: str | None,
    requested_at: str | None,
) -> RunContext:
    if run_id is not None and (workspace.root / run_id).exists():
        run = load_order_run(workspace, run_id)
        if run.crew_id != crew_id:
            raise CrewFactoryError(
                f"Existing run '{run_id}' belongs to crew '{run.crew_id}', not '{crew_id}'"
            )
        return run

    return workspace.create_run(
        crew_id=crew_id,
        input_summary=build_user_request_preview(user_request),
        run_id=run_id,
        metadata={"requested_at": requested_at or datetime.now(UTC).isoformat()},
    )


def _ensure_run_request_artifact(
    workspace: TaskWorkspace,
    run: RunContext,
    user_request: str,
) -> None:
    request_path = run.run_dir / "request.md"
    if request_path.exists():
        return
    workspace.write_run_artifact(run, "request.md", build_request_markdown(user_request))


def _resolve_requested_at(run: RunContext, requested_at: str | None) -> str:
    if requested_at is not None:
        return requested_at
    payload = json.loads(run.metadata_path.read_text(encoding="utf-8"))
    value = payload.get("requested_at")
    if value is None:
        return datetime.now(UTC).isoformat()
    return str(value)


def _write_run_status(
    workspace: TaskWorkspace,
    run: RunContext,
    status: str,
    crew_id: str,
    user_request: str,
    requested_at: str,
    started_at: str | None = None,
    finished_at: str | None = None,
    failure_file: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    record = OrderStatusRecord(
        order_id=run.run_id,
        crew_id=crew_id,
        status=status,  # type: ignore[arg-type]
        user_request_preview=build_user_request_preview(user_request),
        requested_at=requested_at,
        summary_file=str(run.summary_path),
        started_at=started_at,
        finished_at=finished_at,
        failure_file=failure_file,
        error_type=error_type,
        error_message=error_message,
    )
    write_order_status(workspace, run, record)


def _read_user_request(args: argparse.Namespace, project_root: Path) -> str:
    if args.input:
        return args.input.strip()
    input_path = project_root / args.input_file
    return input_path.read_text(encoding="utf-8").strip()


def _build_task_input_markdown(task_id: str, description: str, user_request: str) -> str:
    return (
        f"# Task 입력\n\n"
        f"- Task ID: `{task_id}`\n\n"
        f"## 사용자 요청\n\n{user_request}\n\n"
        f"## Task 설명\n\n{description}\n"
    )


def _task_output_to_markdown(task_id: str, output: object | None) -> str:
    if output is None:
        return f"# {task_id}\n\n_출력이 기록되지 않았습니다._\n"

    # CrewAI TaskOutput이 있으면 raw를 우선 사용하고, 없으면 문자열 표현으로 폴백한다.
    raw_output = getattr(output, "raw", None)
    body = str(raw_output if raw_output else output).strip()
    if not body:
        body = "_출력이 기록되지 않았습니다._"
    return f"# {task_id}\n\n{body}\n"


def _build_run_summary(crew_id: str, user_request: str, result: object) -> str:
    return (
        f"# 실행 요약\n\n"
        f"- Crew ID: `{crew_id}`\n"
        f"- 요청 기록 시각: `{datetime.now(UTC).isoformat()}`\n\n"
        f"## 사용자 요청\n\n{user_request}\n\n"
        f"## 최종 결과\n\n{str(result).strip()}\n"
    )


def _persist_run_failure(
    workspace: TaskWorkspace,
    run: RunContext,
    task_contexts: dict[str, TaskContext],
    spec_tasks: Sequence[CrewTaskSpec],
    crew: object | None,
    crew_id: str,
    user_request: str,
    error: Exception,
) -> Path:
    failed_at = datetime.now(UTC).isoformat()
    error_payload = _build_error_payload(error)

    _persist_completed_task_results(
        workspace=workspace,
        task_contexts=task_contexts,
        spec_tasks=spec_tasks,
        crew=crew,
    )

    failed_task_id = _detect_failed_task_id(spec_tasks=spec_tasks, crew=crew)
    failed_task_result_path = _persist_failed_task_artifacts(
        workspace=workspace,
        task_contexts=task_contexts,
        failed_task_id=failed_task_id,
        failed_at=failed_at,
        error=error,
        error_payload=error_payload,
    )

    run_failure_payload = {
        "crew_id": crew_id,
        "failed_at": failed_at,
        "failed_task_id": failed_task_id,
        **error_payload,
    }
    run_failure_json_path = run.run_dir / "failure.json"
    workspace.write_run_json_artifact(run, "failure.json", run_failure_payload)

    run_summary = _build_failure_run_summary(
        crew_id=crew_id,
        user_request=user_request,
        failed_at=failed_at,
        failed_task_id=failed_task_id,
        error=error,
        error_payload=error_payload,
        run_failure_json_path=run_failure_json_path,
    )
    final_result_path = failed_task_result_path or run.summary_path
    return workspace.write_run_summary(
        run,
        summary_markdown=run_summary,
        metadata={
            "status": "failed",
            "failed_at": failed_at,
            "failed_task_id": failed_task_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "failure_artifact_path": str(run_failure_json_path),
            "final_result_path": str(final_result_path),
        },
    )


def _persist_completed_task_results(
    workspace: TaskWorkspace,
    task_contexts: dict[str, TaskContext],
    spec_tasks: Sequence[CrewTaskSpec],
    crew: object | None,
) -> None:
    crew_tasks = getattr(crew, "tasks", None)
    if not crew_tasks:
        return

    for crew_task, task_spec in zip(crew_tasks, spec_tasks, strict=False):
        task_output = getattr(crew_task, "output", None)
        if task_output is None:
            break
        task_id = task_spec.id
        workspace.write_task_result(
            task_contexts[task_id],
            result_markdown=_task_output_to_markdown(task_id, task_output),
            metadata={"status": "completed"},
        )


def _detect_failed_task_id(spec_tasks: Sequence[CrewTaskSpec], crew: object | None) -> str | None:
    if not spec_tasks:
        return None

    crew_tasks = getattr(crew, "tasks", None)
    if not crew_tasks:
        return spec_tasks[0].id

    for crew_task, task_spec in zip(crew_tasks, spec_tasks, strict=False):
        if getattr(crew_task, "output", None) is None:
            return task_spec.id
    return None


def _persist_failed_task_artifacts(
    workspace: TaskWorkspace,
    task_contexts: dict[str, TaskContext],
    failed_task_id: str | None,
    failed_at: str,
    error: Exception,
    error_payload: Mapping[str, object],
) -> Path | None:
    if failed_task_id is None:
        return None

    task_context = task_contexts[failed_task_id]
    task_failure_json_path = task_context.task_dir / "failure.json"
    workspace.write_task_json_artifact(
        task_context,
        "failure.json",
        {
            "failed_at": failed_at,
            "task_id": failed_task_id,
            **dict(error_payload),
        },
    )
    return workspace.write_task_result(
        task_context,
        result_markdown=_build_task_failure_markdown(
            task_id=failed_task_id,
            failed_at=failed_at,
            error=error,
            error_payload=error_payload,
            task_failure_json_path=task_failure_json_path,
        ),
        metadata={
            "status": "failed",
            "failed_at": failed_at,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "failure_artifact_path": str(task_failure_json_path),
        },
    )


def _build_error_payload(error: Exception) -> dict[str, object]:
    payload: dict[str, object] = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    if isinstance(error, CodexExecutionError):
        payload.update(error.details.to_dict())
    return payload


def _build_task_failure_markdown(
    task_id: str,
    failed_at: str,
    error: Exception,
    error_payload: Mapping[str, object],
    task_failure_json_path: Path,
) -> str:
    sections = [
        f"# {task_id}",
        "",
        "## 상태",
        "",
        "- `failed`",
        f"- 실패 시각: `{failed_at}`",
        "",
        "## 오류",
        "",
        f"- 타입: `{type(error).__name__}`",
        f"- 메시지: {str(error)}",
        "",
        "## 진단",
        "",
        f"- 상세 JSON: `{task_failure_json_path}`",
    ]
    sections.extend(_build_failure_detail_lines(error_payload))
    return "\n".join(sections) + "\n"


def _build_failure_run_summary(
    crew_id: str,
    user_request: str,
    failed_at: str,
    failed_task_id: str | None,
    error: Exception,
    error_payload: Mapping[str, object],
    run_failure_json_path: Path,
) -> str:
    sections = [
        "# 실행 요약",
        "",
        f"- Crew ID: `{crew_id}`",
        f"- 요청 기록 시각: `{datetime.now(UTC).isoformat()}`",
        "- 상태: `failed`",
        f"- 실패 시각: `{failed_at}`",
    ]
    if failed_task_id is not None:
        sections.append(f"- 실패 Task: `{failed_task_id}`")

    sections.extend(
        [
            "",
            "## 사용자 요청",
            "",
            user_request,
            "",
            "## 오류",
            "",
            f"- 타입: `{type(error).__name__}`",
            f"- 메시지: {str(error)}",
            f"- 실행 상세 JSON: `{run_failure_json_path}`",
        ]
    )
    sections.extend(_build_failure_detail_lines(error_payload))
    sections.append("")
    return "\n".join(sections)


def _build_failure_detail_lines(error_payload: Mapping[str, object]) -> list[str]:
    lines: list[str] = []
    if reason := error_payload.get("reason"):
        lines.append(f"- 원인 분류: `{reason}`")
    if returncode := error_payload.get("returncode"):
        lines.append(f"- 반환 코드: `{returncode}`")
    if timeout_seconds := error_payload.get("timeout_seconds"):
        lines.append(f"- 타임아웃: `{timeout_seconds}`초")
    command = error_payload.get("command")
    if isinstance(command, list) and command:
        rendered = " ".join(str(part) for part in command)
        lines.append(f"- 명령: `{rendered}`")
    if cwd := error_payload.get("cwd"):
        lines.append(f"- 작업 디렉터리: `{cwd}`")

    stderr = error_payload.get("stderr")
    if isinstance(stderr, str) and stderr:
        lines.extend(["", "### stderr", "", "```text", stderr, "```"])

    stdout = error_payload.get("stdout")
    if isinstance(stdout, str) and stdout:
        lines.extend(["", "### stdout", "", "```text", stdout, "```"])

    output_text = error_payload.get("output_text")
    if isinstance(output_text, str) and output_text:
        lines.extend(["", "### output_text", "", "```text", output_text, "```"])

    return lines


def _build_cli_failure_message(
    crew_id: str,
    run: RunContext,
    failure_summary_path: Path | None,
    error: Exception,
    persistence_error: WorkspaceError | None,
) -> str:
    lines = [
        f"Crew 실행이 실패했습니다: {crew_id}",
        f"- 원인: {type(error).__name__}: {error}",
        f"- Run 디렉터리: {run.run_dir}",
    ]
    if failure_summary_path is not None:
        lines.append(f"- 실패 요약: {failure_summary_path}")
    if persistence_error is not None:
        lines.append(f"- 실패 산출물 기록 중 추가 오류: {persistence_error}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
