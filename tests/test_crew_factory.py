from __future__ import annotations

from pathlib import Path

import pytest

from inhouse_crew.crew_factory import CrewFactory
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
