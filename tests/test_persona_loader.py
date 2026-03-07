from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from inhouse_crew.persona_loader import load_agent_persona, load_crew_spec, load_registry


def test_load_registry_reads_sample_configs() -> None:
    agents, crews = load_registry(Path("configs"))

    assert set(agents) == {"developer", "planner", "reviewer"}
    assert set(crews) == {
        "coding_session",
        "feature_delivery",
        "product_discovery",
        "quickstart",
        "review_session",
    }
    assert crews["feature_delivery"].tasks[0].agent == "planner"


def test_load_agent_persona_rejects_missing_id(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text(
        "role: Missing Id\n"
        "goal: test\n"
        "backstory: test\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_agent_persona(invalid_path)


def test_load_crew_spec_rejects_non_mapping(tmp_path: Path) -> None:
    invalid_path = tmp_path / "crew.yaml"
    invalid_path.write_text("- not-a-mapping\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_crew_spec(invalid_path)
