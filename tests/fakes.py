from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from crewai.events import TaskCompletedEvent, TaskFailedEvent, TaskStartedEvent
from crewai.events.event_bus import crewai_event_bus
from crewai.tasks.task_output import TaskOutput

from inhouse_crew.llms import CodexExecutionError, CodexFailureDetails
from inhouse_crew.persona_loader import load_registry
from inhouse_crew.settings_loader import AppSettings


class FakeCrewTask:
    def __init__(self, name: str) -> None:
        self.name = name
        self.output = None
        self.agent = SimpleNamespace(role=f"agent-for-{name}")
        self.output_file: str | None = None
        self.start_time = None
        self.end_time = None
        self._inhouse_llm_telemetry: dict[str, object] | None = None


class FakeCrew:
    def __init__(self, task_names: list[str]) -> None:
        self.tasks = [FakeCrewTask(name) for name in task_names]

    def kickoff(self, inputs: dict[str, str]) -> str:
        for task in self.tasks:
            crewai_event_bus.emit(task, TaskStartedEvent(context="", task=task))
            raw_output = f"Task {task.name}: {inputs['user_request']}"
            task._inhouse_llm_telemetry = {
                "prompt_chars": len(raw_output) + 42,
                "llm_started_at": "2026-03-08T00:00:00+00:00",
                "llm_finished_at": "2026-03-08T00:00:01+00:00",
                "llm_elapsed_seconds": 1.0,
            }
            if task.output_file:
                output_path = Path(task.output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(raw_output, encoding="utf-8")
            task.output = TaskOutput(
                name=task.name,
                description=task.name,
                expected_output=f"Expected output for {task.name}",
                raw=raw_output,
                agent=task.agent.role,
            )
            crewai_event_bus.emit(task, TaskCompletedEvent(output=task.output, task=task))
        crewai_event_bus.flush()
        return "All tasks completed"


class FakeFailingCrew(FakeCrew):
    def kickoff(self, inputs: dict[str, str]) -> str:
        task = self.tasks[0]
        crewai_event_bus.emit(task, TaskStartedEvent(context="", task=task))
        task._inhouse_llm_telemetry = {
            "prompt_chars": len(inputs["user_request"]) + 10,
            "llm_started_at": "2026-03-08T00:00:00+00:00",
            "llm_finished_at": "2026-03-08T00:00:02+00:00",
            "llm_elapsed_seconds": 2.0,
        }
        crewai_event_bus.emit(
            task,
            TaskFailedEvent(
                error="Codex command not found: definitely-missing-command",
                task=task,
            ),
        )
        crewai_event_bus.flush()
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

    def create_crew(
        self,
        crew_id: str,
        output_file_map: dict[str, str] | None = None,
    ) -> FakeCrew:
        crew = FakeCrew([task.id for task in self.crews[crew_id].tasks])
        crew._inhouse_knowledge_reset_applied = False
        if output_file_map:
            for task in crew.tasks:
                task.output_file = output_file_map.get(task.name)
        return crew


class FailingFactory(FakeFactory):
    def create_crew(
        self,
        crew_id: str,
        output_file_map: dict[str, str] | None = None,
    ) -> FakeFailingCrew:
        crew = FakeFailingCrew([task.id for task in self.crews[crew_id].tasks])
        crew._inhouse_knowledge_reset_applied = False
        if output_file_map:
            for task in crew.tasks:
                task.output_file = output_file_map.get(task.name)
        return crew


__all__ = [
    "FakeCrew",
    "FakeCrewTask",
    "FakeFactory",
    "FakeFailingCrew",
    "FailingFactory",
]
