from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool

from .llms import CodexCliLLM
from .persona_loader import AgentPersona, CrewSpec, load_registry
from .settings_loader import AppSettings, load_settings
from .tools import ToolRegistryError, build_tool_registry


class CrewFactoryError(ValueError):
    """Raised when a crew or dependency cannot be constructed."""


class CrewFactory:
    def __init__(
        self,
        settings: AppSettings,
        personas: dict[str, AgentPersona],
        crews: dict[str, CrewSpec],
        project_root: Path | None = None,
    ) -> None:
        self.settings = settings
        self.personas = personas
        self.crews = crews
        self.project_root = project_root or Path.cwd()
        # 같은 LLM 참조를 여러 에이전트가 공유할 수 있게 인스턴스를 캐시한다.
        self._llm_cache: dict[str, Any] = {}
        self._tool_registry = build_tool_registry(
            project_root=self.project_root,
            workspace_root=(self.project_root / self.settings.workspace_root).resolve(),
        )

    @classmethod
    def from_paths(
        cls,
        config_root: Path,
        settings_path: Path,
        project_root: Path | None = None,
        env_file: Path | None = None,
    ) -> "CrewFactory":
        personas, crews = load_registry(config_root)
        settings = load_settings(settings_path=settings_path, env_file=env_file)
        return cls(
            settings=settings,
            personas=personas,
            crews=crews,
            project_root=project_root or config_root.parent,
        )

    def create_crew(self, crew_id: str) -> Crew:
        spec = self._get_crew_spec(crew_id)
        # YAML에 선언된 agent/task 정의를 CrewAI 객체로 조립하는 중심 레이어다.
        agents = {persona_id: self.create_agent(persona_id) for persona_id in spec.agents}
        tasks = [self._create_task(task_spec, agents) for task_spec in spec.tasks]

        return Crew(
            agents=list(agents.values()),
            tasks=tasks,
            process=Process(spec.process),
            verbose=True,
        )

    def create_agent(self, persona_id: str) -> Agent:
        persona = self._get_persona(persona_id)
        return Agent(
            role=persona.role,
            goal=persona.goal,
            backstory=self._build_backstory(persona),
            allow_delegation=persona.allow_delegation,
            verbose=persona.verbose,
            llm=self._resolve_llm(persona.llm or self.settings.default_llm),
            tools=self._resolve_tools(persona.tools),
        )

    def _create_task(self, task_spec: Any, agents: dict[str, Agent]) -> Task:
        if task_spec.agent not in agents:
            raise CrewFactoryError(
                f"Task '{task_spec.id}' references unknown agent '{task_spec.agent}'"
            )

        return Task(
            name=task_spec.id,
            description=task_spec.description,
            expected_output=task_spec.expected_output,
            agent=agents[task_spec.agent],
            markdown=True,
        )

    def _resolve_llm(self, llm_ref: str) -> Any:
        if llm_ref in self._llm_cache:
            return self._llm_cache[llm_ref]

        # 현재는 로컬 Codex 세션만 커스텀 LLM으로 감싸고, 나머지는 CrewAI 기본 문자열 참조에 맡긴다.
        if llm_ref == "codex-local-oauth":
            llm = CodexCliLLM(
                model=llm_ref,
                codex_command=self.settings.codex_command,
                codex_model=self.settings.codex_model,
                timeout_seconds=self.settings.timeout_seconds,
                retry_count=self.settings.retry_count,
                workdir=self.project_root,
            )
        else:
            llm = llm_ref

        self._llm_cache[llm_ref] = llm
        return llm

    def _resolve_tools(self, tool_names: list[str]) -> list[BaseTool]:
        resolved: list[BaseTool] = []
        missing: list[str] = []

        # 도구 이름 검증은 조립 단계에서 끝내서 실행 중 런타임 오류를 줄인다.
        for tool_name in tool_names:
            tool = self._tool_registry.get(tool_name)
            if tool is None:
                missing.append(tool_name)
            else:
                resolved.append(tool)

        if missing:
            raise ToolRegistryError(f"Unknown tools requested: {', '.join(sorted(missing))}")

        return resolved

    def _get_persona(self, persona_id: str) -> AgentPersona:
        try:
            return self.personas[persona_id]
        except KeyError as error:
            raise CrewFactoryError(f"Unknown persona '{persona_id}'") from error

    def _get_crew_spec(self, crew_id: str) -> CrewSpec:
        try:
            return self.crews[crew_id]
        except KeyError as error:
            raise CrewFactoryError(f"Unknown crew '{crew_id}'") from error

    def _build_backstory(self, persona: AgentPersona) -> str:
        if not persona.rules:
            return persona.backstory

        # YAML rules를 backstory 뒤에 합쳐 에이전트 프롬프트에 일관되게 반영한다.
        rules = "\n".join(f"- {rule}" for rule in persona.rules)
        return f"{persona.backstory}\n\nOperating rules:\n{rules}"
