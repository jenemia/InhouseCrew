from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.knowledge.knowledge import Knowledge
from crewai.knowledge.source.base_knowledge_source import BaseKnowledgeSource
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource
from crewai.knowledge.storage.knowledge_storage import KnowledgeStorage
from crewai.memory.storage.lancedb_storage import LanceDBStorage
from crewai.memory.unified_memory import Memory
from crewai.rag.chromadb.config import ChromaDBConfig
from crewai.rag.config.utils import set_rag_config
from crewai.rag.embeddings.factory import build_embedder
from crewai.tools import BaseTool

from .llms import CodexCliLLM
from .persona_loader import AgentPersona, CrewSpec, load_registry
from .settings_loader import AppSettings, load_settings
from .tools import ToolRegistryError, build_tool_registry


class CrewFactoryError(ValueError):
    """Raised when a crew or dependency cannot be constructed."""


@dataclass(slots=True, frozen=True)
class KnowledgeBuildResult:
    knowledge: Knowledge
    knowledge_sources: list[BaseKnowledgeSource]
    reset_applied: bool


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

    def create_crew(
        self,
        crew_id: str,
        output_file_map: dict[str, str] | None = None,
    ) -> Crew:
        spec = self._get_crew_spec(crew_id)
        # YAML에 선언된 agent/task 정의를 CrewAI 객체로 조립하는 중심 레이어다.
        agents = {persona_id: self.create_agent(persona_id) for persona_id in spec.agents}
        tasks = {
            task_spec.id: self._create_task(
                task_spec,
                agents,
                output_file=output_file_map.get(task_spec.id) if output_file_map else None,
            )
            for task_spec in spec.tasks
        }
        self._apply_task_contexts(spec, tasks)
        crew_kwargs: dict[str, Any] = {}
        knowledge_sources: list[BaseKnowledgeSource] = []
        knowledge_reset_applied = False

        if spec.knowledge_files or spec.memory:
            embedder = self._build_crew_embedder(crew_id)
            if spec.knowledge_files:
                knowledge_result = self._prepare_crew_knowledge(
                    crew_id,
                    spec.knowledge_files,
                    embedder,
                )
                knowledge_sources = knowledge_result.knowledge_sources
                knowledge_reset_applied = knowledge_result.reset_applied
                crew_kwargs["knowledge"] = knowledge_result.knowledge
            if spec.memory:
                crew_kwargs["memory"] = self._build_crew_memory(crew_id, embedder)

        crew = Crew(
            agents=list(agents.values()),
            tasks=[tasks[task_spec.id] for task_spec in spec.tasks],
            process=Process(spec.process),
            verbose=True,
            **crew_kwargs,
        )
        if knowledge_sources:
            crew.knowledge_sources = knowledge_sources
        crew._inhouse_knowledge_reset_applied = knowledge_reset_applied
        return crew

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

    def _create_task(
        self,
        task_spec: Any,
        agents: dict[str, Agent],
        output_file: str | None = None,
    ) -> Task:
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
            output_file=output_file,
        )

    def _apply_task_contexts(self, spec: CrewSpec, tasks: dict[str, Task]) -> None:
        task_order = {task_spec.id: index for index, task_spec in enumerate(spec.tasks)}
        for task_spec in spec.tasks:
            if not task_spec.context_tasks:
                continue
            for context_task_id in task_spec.context_tasks:
                if context_task_id not in tasks:
                    raise CrewFactoryError(
                        f"Task '{task_spec.id}' references unknown context task "
                        f"'{context_task_id}'"
                    )
                if task_order[context_task_id] >= task_order[task_spec.id]:
                    raise CrewFactoryError(
                        f"Task '{task_spec.id}' must reference only earlier context tasks"
                    )
            tasks[task_spec.id].context = [tasks[task_id] for task_id in task_spec.context_tasks]

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

    def _build_crew_embedder(self, crew_id: str) -> Any:
        if self.settings.embedder is None:
            raise CrewFactoryError(
                f"Crew '{crew_id}' enables knowledge/memory but no embedder is configured"
            )
        try:
            embedder = build_embedder(self.settings.embedder)
            embedder(["crew-init-probe"])
            return embedder
        except Exception as error:
            raise CrewFactoryError(
                f"Failed to initialize embedder for crew '{crew_id}': {error}"
            ) from error

    def _prepare_crew_knowledge(
        self,
        crew_id: str,
        knowledge_files: list[str],
        embedder: Any,
    ) -> KnowledgeBuildResult:
        resolved_paths = self._resolve_knowledge_file_paths(crew_id, knowledge_files)
        knowledge_sources = self._build_knowledge_sources(resolved_paths)
        source_signature = self._compute_knowledge_signature(resolved_paths)
        reset_applied = self._should_reset_knowledge(crew_id, source_signature)

        self._configure_knowledge_rag(embedder)
        knowledge = self._build_crew_knowledge(
            crew_id,
            knowledge_sources,
            reset_applied=reset_applied,
        )
        self._write_knowledge_signature(crew_id, source_signature, resolved_paths)
        return KnowledgeBuildResult(
            knowledge=knowledge,
            knowledge_sources=knowledge_sources,
            reset_applied=reset_applied,
        )

    def _resolve_knowledge_file_paths(
        self, crew_id: str, knowledge_files: list[str]
    ) -> list[Path]:
        resolved_paths: list[Path] = []
        missing_paths: list[str] = []

        for relative_path in knowledge_files:
            file_path = (self.project_root / relative_path).resolve()
            if not file_path.is_file():
                missing_paths.append(relative_path)
            else:
                resolved_paths.append(file_path)

        if missing_paths:
            raise CrewFactoryError(
                f"Crew '{crew_id}' references missing knowledge files: {', '.join(missing_paths)}"
            )

        return resolved_paths

    def _build_knowledge_sources(self, resolved_paths: list[Path]) -> list[BaseKnowledgeSource]:
        return [TextFileKnowledgeSource(file_paths=resolved_paths)]

    def _configure_knowledge_rag(self, embedder: Any) -> None:
        persist_directory = (
            self.project_root / self.settings.crewai_storage_root / "knowledge"
        ).resolve()
        persist_directory.mkdir(parents=True, exist_ok=True)
        config = ChromaDBConfig(embedding_function=embedder)
        config.settings.persist_directory = str(persist_directory)
        config.settings.allow_reset = True
        config.settings.is_persistent = True
        config.settings.anonymized_telemetry = False
        set_rag_config(config)

    def _build_crew_knowledge(
        self,
        crew_id: str,
        knowledge_sources: list[BaseKnowledgeSource],
        *,
        reset_applied: bool,
    ) -> Knowledge:
        try:
            knowledge = Knowledge(
                collection_name=crew_id,
                sources=knowledge_sources,
                storage=KnowledgeStorage(collection_name=crew_id),
            )
            if reset_applied:
                knowledge.reset()
            knowledge.add_sources()
            return knowledge
        except Exception as error:
            raise CrewFactoryError(
                f"Failed to initialize knowledge for crew '{crew_id}': {error}"
            ) from error

    def _compute_knowledge_signature(self, resolved_paths: list[Path]) -> str:
        digest = hashlib.sha256()
        for file_path in resolved_paths:
            relative_path = file_path.relative_to(self.project_root).as_posix()
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(file_path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()

    def _should_reset_knowledge(self, crew_id: str, source_signature: str) -> bool:
        signature_path = self._knowledge_signature_path(crew_id)
        if not signature_path.exists():
            return True
        try:
            payload = json.loads(signature_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return True
        return payload.get("source_signature") != source_signature

    def _write_knowledge_signature(
        self,
        crew_id: str,
        source_signature: str,
        resolved_paths: list[Path],
    ) -> None:
        signature_path = self._knowledge_signature_path(crew_id)
        signature_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "crew_id": crew_id,
            "source_signature": source_signature,
            "files": [path.relative_to(self.project_root).as_posix() for path in resolved_paths],
        }
        signature_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _knowledge_signature_path(self, crew_id: str) -> Path:
        return (
            self.project_root
            / self.settings.crewai_storage_root
            / "knowledge"
            / "source-signatures"
            / f"{crew_id}.json"
        ).resolve()

    def _build_crew_memory(self, crew_id: str, embedder: Any) -> Memory:
        memory_path = (
            self.project_root
            / self.settings.crewai_storage_root
            / "memory"
            / crew_id
        ).resolve()
        memory_path.mkdir(parents=True, exist_ok=True)
        try:
            return Memory(
                llm=self._resolve_llm(self.settings.default_llm),
                storage=LanceDBStorage(path=str(memory_path)),
                embedder=embedder,
            )
        except Exception as error:
            raise CrewFactoryError(
                f"Failed to initialize memory for crew '{crew_id}': {error}"
            ) from error
