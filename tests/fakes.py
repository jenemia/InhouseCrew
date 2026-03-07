from __future__ import annotations

from pathlib import Path

from inhouse_crew.llms import CodexExecutionError, CodexFailureDetails
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


__all__ = [
    "FakeCrew",
    "FakeCrewTask",
    "FakeFactory",
    "FakeFailingCrew",
    "FakeTaskOutput",
    "FailingFactory",
]
