from __future__ import annotations

import json
from pathlib import Path

import pytest

from inhouse_crew.llms import CodexExecutionError, CodexFailureDetails
from inhouse_crew.main import CrewRunExecutionError, main, run_crew
from inhouse_crew.persona_loader import load_registry
from inhouse_crew.settings_loader import AppSettings


class FakeTaskOutput:
    def __init__(self, raw: str) -> None:
        self.raw = raw


class FakeCrewTask:
    def __init__(self, name: str) -> None:
        self.name = name
        self.output = None


class FakeCrew:
    def __init__(self, task_names: list[str]) -> None:
        self.tasks = [FakeCrewTask(name) for name in task_names]

    def kickoff(self, inputs: dict[str, str]) -> str:
        for task in self.tasks:
            task.output = FakeTaskOutput(f"Task {task.name}: {inputs['user_request']}")
        return "All tasks completed"


class FakeFailingCrew(FakeCrew):
    def kickoff(self, inputs: dict[str, str]) -> str:
        raise CodexExecutionError(
            "Codex command not found: definitely-missing-command",
            details=CodexFailureDetails(
                reason="command_not_found",
                command=["definitely-missing-command"],
                cwd=str(Path.cwd()),
            ),
        )


class FakeFactory:
    def __init__(self, config_root: Path) -> None:
        _, crews = load_registry(config_root)
        self.crews = crews
        self.settings = AppSettings.model_validate({"workspace_root": "workspace/runs"})

    def create_crew(self, crew_id: str) -> FakeCrew:
        return FakeCrew([task.id for task in self.crews[crew_id].tasks])


class FailingFactory(FakeFactory):
    def create_crew(self, crew_id: str) -> FakeFailingCrew:
        return FakeFailingCrew([task.id for task in self.crews[crew_id].tasks])


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

    task_result = next((tmp_path / "workspace" / "runs").glob("*/summarize_request/result.md"))
    assert "Summarize the request." in task_result.read_text(encoding="utf-8")


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
        (run_dir / "summarize_request" / "metadata.json").read_text(encoding="utf-8")
    )

    assert run_metadata["status"] == "failed"
    assert run_metadata["failed_task_id"] == "summarize_request"
    assert task_metadata["status"] == "failed"
    assert (run_dir / "failure.json").exists()
    assert (run_dir / "summarize_request" / "failure.json").exists()
    assert "Codex command not found" in (run_dir / "summary.md").read_text(encoding="utf-8")
    assert "Codex command not found" in (
        run_dir / "summarize_request" / "result.md"
    ).read_text(encoding="utf-8")


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
