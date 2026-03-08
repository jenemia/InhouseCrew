from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class AgentPersona(BaseModel):
    # persona는 코드가 아니라 데이터이므로, 허용 필드를 엄격하게 검증한다.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    role: str
    goal: str
    backstory: str
    rules: list[str] = Field(default_factory=list)
    allow_delegation: bool = False
    verbose: bool = False
    llm: str | None = None
    tools: list[str] = Field(default_factory=list)


class CrewTaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    agent: str
    description: str
    expected_output: str
    output_artifact: str | None = None
    context_tasks: list[str] = Field(default_factory=list)


class CrewOutputPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    save_markdown: bool = True
    include_metadata: bool = True


class CrewSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str
    name: str
    process: Literal["sequential", "hierarchical"] = "sequential"
    agents: list[str]
    tasks: list[CrewTaskSpec]
    knowledge_files: list[str] = Field(default_factory=list)
    memory: bool = False
    output_policy: CrewOutputPolicy = Field(default_factory=CrewOutputPolicy)


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    # 로더는 YAML 파싱과 구조 검증만 담당하고, 실제 조립은 팩토리에 맡긴다.
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at {path}, got {type(data).__name__}")
    return data


def load_agent_persona(path: Path) -> AgentPersona:
    return AgentPersona.model_validate(_load_yaml_dict(path))


def load_agent_personas(directory: Path) -> dict[str, AgentPersona]:
    personas: dict[str, AgentPersona] = {}
    for path in sorted(directory.glob("*.yaml")):
        persona = load_agent_persona(path)
        personas[persona.id] = persona
    return personas


def load_crew_spec(path: Path) -> CrewSpec:
    return CrewSpec.model_validate(_load_yaml_dict(path))


def load_crew_specs(directory: Path) -> dict[str, CrewSpec]:
    specs: dict[str, CrewSpec] = {}
    for path in sorted(directory.glob("*.yaml")):
        spec = load_crew_spec(path)
        specs[spec.id] = spec
    return specs


def load_registry(config_root: Path) -> tuple[dict[str, AgentPersona], dict[str, CrewSpec]]:
    # agent/crew registry를 한 번에 읽어 상위 레이어가 참조하기 쉽게 만든다.
    agents_dir = config_root / "agents"
    crews_dir = config_root / "crews"
    return load_agent_personas(agents_dir), load_crew_specs(crews_dir)


__all__ = [
    "AgentPersona",
    "CrewOutputPolicy",
    "CrewSpec",
    "CrewTaskSpec",
    "ValidationError",
    "load_agent_persona",
    "load_agent_personas",
    "load_crew_spec",
    "load_crew_specs",
    "load_registry",
]
