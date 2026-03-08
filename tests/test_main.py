from __future__ import annotations

import json
from pathlib import Path

import pytest

from inhouse_crew.main import CrewRunExecutionError, main, run_crew
from tests.fakes import FailingFactory, FakeFactory


def test_run_crew_writes_summary_and_task_outputs(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace").mkdir()

    factory = FakeFactory(repo_root / "configs")
    summary_path = run_crew(
        factory=factory,
        crew_id="quickstart",
        user_request="Summarize the request.",
        project_root=tmp_path,
    )

    assert summary_path.name == "summary.md"
    assert summary_path.exists()
    assert "All tasks completed" in summary_path.read_text(encoding="utf-8")
    run_dir = summary_path.parent
    status_payload = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))

    task_result = next((tmp_path / "workspace" / "runs").glob("*/1.planner/result.md"))
    assert "Summarize the request." in task_result.read_text(encoding="utf-8")
    assert status_payload["status"] == "completed"
    assert status_payload["task_statuses"]["summarize_request"]["status"] == "done"
    assert status_payload["task_statuses"]["summarize_request"]["task_dir_name"] == "1.planner"
    assert status_payload["task_statuses"]["summarize_request"]["prompt_chars"] > 0
    assert status_payload["task_statuses"]["summarize_request"]["llm_elapsed_seconds"] == 1.0
    assert status_payload["task_statuses"]["summarize_request"]["knowledge_reset_applied"] is False
    assert (run_dir / "1.planner" / "status.json").exists()
    assert (run_dir / "1.planner" / "summary.md").exists()


def test_run_crew_persists_failure_artifacts(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    (tmp_path / "workspace").mkdir()

    factory = FailingFactory(repo_root / "configs")

    with pytest.raises(CrewRunExecutionError, match="Crew 실행이 실패했습니다"):
        run_crew(
            factory=factory,
            crew_id="quickstart",
            user_request="실패를 재현해줘.",
            project_root=tmp_path,
        )

    run_dir = next((tmp_path / "workspace" / "runs").glob("*"))
    run_metadata = json.loads((run_dir / "run-metadata.json").read_text(encoding="utf-8"))
    task_metadata = json.loads(
        (run_dir / "1.planner" / "metadata.json").read_text(encoding="utf-8")
    )

    assert run_metadata["status"] == "failed"
    assert run_metadata["failed_task_id"] == "summarize_request"
    assert task_metadata["task_dir_name"] == "1.planner"
    assert task_metadata["status"] == "failed"
    task_status = json.loads((run_dir / "1.planner" / "status.json").read_text(encoding="utf-8"))
    run_status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    assert task_status["status"] == "failed"
    assert task_status["task_dir_name"] == "1.planner"
    assert task_status["prompt_chars"] > 0
    assert task_status["llm_elapsed_seconds"] == 2.0
    assert run_status["task_statuses"]["summarize_request"]["status"] == "failed"
    assert run_status["task_statuses"]["summarize_request"]["task_dir_name"] == "1.planner"
    assert (run_dir / "failure.json").exists()
    assert (run_dir / "1.planner" / "failure.json").exists()
    assert "Codex command not found" in (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "Codex command not found" in (run_dir / "1.planner" / "result.md").read_text(
        encoding="utf-8"
    )


def test_main_returns_nonzero_with_concise_failure_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_run_from_args(args: object) -> Path:
        raise CrewRunExecutionError(
            "Crew 실행이 실패했습니다: quickstart",
            run_dir=Path("/tmp/run-001"),
            summary_path=Path("/tmp/run-001/summary.md"),
        )

    monkeypatch.setattr("inhouse_crew.main.run_from_args", fake_run_from_args)

    exit_code = main(["run", "--input", "실패 재현"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Crew 실행이 실패했습니다" in captured.err
