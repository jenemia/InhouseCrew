from __future__ import annotations

from pathlib import Path

import pytest
from crewai.knowledge.knowledge import Knowledge
from crewai.knowledge.storage.knowledge_storage import KnowledgeStorage

from inhouse_crew.crew_factory import CrewFactory, CrewFactoryError, KnowledgeBuildResult
from inhouse_crew.persona_loader import AgentPersona, load_registry
from inhouse_crew.settings_loader import load_settings
from inhouse_crew.tools import ToolRegistryError


def test_crew_factory_creates_feature_delivery_crew() -> None:
    factory = CrewFactory.from_paths(
        config_root=Path("configs"),
        settings_path=Path("configs/settings.yaml"),
        project_root=Path.cwd(),
    )

    crew = factory.create_crew("feature_delivery")

    assert len(crew.agents) == 3
    assert len(crew.tasks) == 3
    assert crew.tasks[0].name == "plan_feature"


def test_crew_factory_creates_game_design_team_crew(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = CrewFactory.from_paths(
        config_root=Path("configs"),
        settings_path=Path("configs/settings.yaml"),
        project_root=Path.cwd(),
    )
    memory_build_calls: list[str] = []
    dummy_knowledge = Knowledge(
        collection_name="game_design_team",
        sources=[],
        storage=KnowledgeStorage(collection_name="game_design_team"),
    )

    monkeypatch.setattr(factory, "_build_crew_embedder", lambda crew_id: object())
    monkeypatch.setattr(
        factory,
        "_prepare_crew_knowledge",
        lambda crew_id, knowledge_files, embedder: KnowledgeBuildResult(
            knowledge=dummy_knowledge,
            knowledge_sources=[],
            reset_applied=True,
        ),
    )
    monkeypatch.setattr(
        factory,
        "_build_crew_memory",
        lambda crew_id, embedder: memory_build_calls.append(crew_id),
    )

    crew = factory.create_crew("game_design_team")

    assert len(crew.agents) == 5
    assert len(crew.tasks) == 5
    assert crew.tasks[0].name == "generate_game_concept"
    assert crew.tasks[-1].name == "synthesize_game_direction"
    assert crew.knowledge is dummy_knowledge
    assert [task.name for task in crew.tasks[1].context] == ["generate_game_concept"]
    assert [task.name for task in crew.tasks[2].context] == [
        "generate_game_concept",
        "define_player_fantasy",
    ]
    assert memory_build_calls == []
    assert not getattr(crew, "_memory", None)
    assert getattr(crew, "_inhouse_knowledge_reset_applied", None) is True


def test_crew_factory_raises_on_missing_knowledge_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    personas, crews = load_registry(Path("configs"))
    settings = load_settings(Path("configs/settings.yaml"))
    crews["game_design_team"] = crews["game_design_team"].model_copy(
        update={"knowledge_files": ["knowledge/game_design_team/missing.md"]}
    )
    factory = CrewFactory(
        settings=settings,
        personas=personas,
        crews=crews,
        project_root=Path.cwd(),
    )
    monkeypatch.setattr(factory, "_build_crew_embedder", lambda crew_id: object())

    with pytest.raises(CrewFactoryError, match="missing knowledge files"):
        factory.create_crew("game_design_team")


def test_crew_factory_raises_on_invalid_context_task_reference() -> None:
    personas, crews = load_registry(Path("configs"))
    settings = load_settings(Path("configs/settings.yaml"))
    invalid_tasks = list(crews["game_design_team"].tasks)
    invalid_tasks[1] = invalid_tasks[1].model_copy(update={"context_tasks": ["missing_task"]})
    crews["game_design_team"] = crews["game_design_team"].model_copy(
        update={"tasks": invalid_tasks}
    )
    factory = CrewFactory(
        settings=settings,
        personas=personas,
        crews=crews,
        project_root=Path.cwd(),
    )

    with pytest.raises(CrewFactoryError, match="unknown context task"):
        factory.create_crew("game_design_team")


def test_crew_factory_resets_knowledge_when_signature_changes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    factory = CrewFactory.from_paths(
        config_root=Path("configs"),
        settings_path=Path("configs/settings.yaml"),
        project_root=Path.cwd(),
    )
    signature_path = tmp_path / "game_design_team.json"
    monkeypatch.setattr(factory, "_knowledge_signature_path", lambda crew_id: signature_path)

    class DummyKnowledge:
        def __init__(self) -> None:
            self.reset_calls = 0
            self.add_sources_calls = 0

        def reset(self) -> None:
            self.reset_calls += 1

        def add_sources(self) -> None:
            self.add_sources_calls += 1

    dummy_knowledge = DummyKnowledge()
    monkeypatch.setattr(
        "inhouse_crew.crew_factory.Knowledge",
        lambda collection_name, sources, storage: dummy_knowledge,
    )

    resolved_paths = [Path("knowledge/game_design_team/project_brief.md").resolve()]
    result = factory._build_crew_knowledge(  # type: ignore[attr-defined]
        "game_design_team",
        factory._build_knowledge_sources(resolved_paths),
        reset_applied=True,
    )
    factory._write_knowledge_signature("game_design_team", "sig-a", resolved_paths)

    assert result is dummy_knowledge
    assert dummy_knowledge.reset_calls == 1
    assert dummy_knowledge.add_sources_calls == 1
    assert factory._should_reset_knowledge("game_design_team", "sig-a") is False
    assert factory._should_reset_knowledge("game_design_team", "sig-b") is True


def test_crew_factory_raises_when_embedder_is_missing() -> None:
    personas, crews = load_registry(Path("configs"))
    settings = load_settings(Path("configs/settings.yaml")).model_copy(update={"embedder": None})
    factory = CrewFactory(
        settings=settings,
        personas=personas,
        crews=crews,
        project_root=Path.cwd(),
    )

    with pytest.raises(CrewFactoryError, match="no embedder is configured"):
        factory.create_crew("game_design_team")


def test_crew_factory_raises_when_embedder_probe_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = CrewFactory.from_paths(
        config_root=Path("configs"),
        settings_path=Path("configs/settings.yaml"),
        project_root=Path.cwd(),
    )

    class BrokenEmbedder:
        def __call__(self, _: list[str]) -> list[object]:
            raise RuntimeError("embedder probe failed")

    monkeypatch.setattr("inhouse_crew.crew_factory.build_embedder", lambda _: BrokenEmbedder())

    with pytest.raises(CrewFactoryError, match="Failed to initialize embedder"):
        factory.create_crew("game_design_team")


def test_crew_factory_raises_on_unknown_tool_reference() -> None:
    personas, crews = load_registry(Path("configs"))
    settings = load_settings(Path("configs/settings.yaml"))
    personas["planner"] = AgentPersona.model_validate(
        {
            **personas["planner"].model_dump(),
            "tools": ["file_read", "missing_tool"],
        }
    )
    factory = CrewFactory(
        settings=settings,
        personas=personas,
        crews=crews,
        project_root=Path.cwd(),
    )

    with pytest.raises(ToolRegistryError, match="missing_tool"):
        factory.create_agent("planner")
