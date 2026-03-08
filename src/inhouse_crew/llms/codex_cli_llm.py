from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crewai import BaseLLM
from pydantic import BaseModel

from .codex_runner import CodexExecutionError, CodexRunner


class CodexCliLLM(BaseLLM):
    def __init__(
        self,
        model: str = "codex-local-oauth",
        codex_command: str = "codex",
        codex_model: str | None = None,
        timeout_seconds: int = 120,
        retry_count: int = 1,
        workdir: str | Path | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model=model, provider="codex", **kwargs)
        self.codex_model = codex_model
        self.runner = CodexRunner(
            codex_command=codex_command,
            model=codex_model,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            workdir=Path(workdir) if workdir is not None else None,
        )

    def call(
        self,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Any | None = None,
        from_agent: Any | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> str | Any:
        # BaseLLM 계약에 맞게 입력을 정규화한 뒤, 실제 실행은 CodexRunner에 위임한다.
        normalized_messages = self._normalize_messages(messages)

        if not self._invoke_before_llm_call_hooks(normalized_messages, from_agent):
            raise ValueError("Codex LLM call blocked by before_llm_call hook")

        prompt = self._build_prompt(
            messages=normalized_messages,
            tools=tools,
            available_functions=available_functions,
            response_model=response_model,
        )
        prompt_chars = len(prompt)
        try:
            result = self.runner.run(prompt)
        except CodexExecutionError as error:
            self._attach_task_telemetry(
                from_task,
                prompt_chars=prompt_chars,
                llm_started_at=error.details.llm_started_at,
                llm_finished_at=error.details.llm_finished_at,
                llm_elapsed_seconds=error.details.llm_elapsed_seconds,
            )
            raise

        self._attach_task_telemetry(
            from_task,
            prompt_chars=result.prompt_chars,
            llm_started_at=result.llm_started_at,
            llm_finished_at=result.llm_finished_at,
            llm_elapsed_seconds=result.llm_elapsed_seconds,
        )

        response_text = result.output_text
        if self.stop:
            response_text = self._apply_stop_words(response_text)

        # CrewAI 훅과 structured output 검증은 프로젝트 레이어에서도 그대로 존중한다.
        response_text = self._invoke_after_llm_call_hooks(
            normalized_messages,
            response_text,
            from_agent,
        )
        self._track_token_usage_internal({})
        return self._validate_structured_output(response_text, response_model)

    def supports_function_calling(self) -> bool:
        # MVP 범위에서는 tool calling을 텍스트 프롬프트로만 안내하고 네이티브 호출은 막는다.
        return False

    def get_context_window_size(self) -> int:
        return 200_000

    def _normalize_messages(self, messages: str | list[dict[str, Any]]) -> list[dict[str, str]]:
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]

        normalized: list[dict[str, str]] = []
        for message in messages:
            role = str(message.get("role", "user"))
            content = self._coerce_content(message.get("content", ""))
            normalized.append({"role": role, "content": content})
        return normalized

    def _coerce_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                # 멀티모달 블록이 와도 최소한 텍스트 프롬프트로 보존되도록 평탄화한다.
                if isinstance(block, dict):
                    if block.get("type") == "text" and "text" in block:
                        parts.append(str(block["text"]))
                    elif "content" in block:
                        parts.append(str(block["content"]))
                    else:
                        parts.append(json.dumps(block, ensure_ascii=True))
                else:
                    parts.append(str(block))
            return "\n".join(part.strip() for part in parts if str(part).strip())
        return str(content).strip()

    def _build_prompt(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None,
        available_functions: dict[str, Any] | None,
        response_model: type[BaseModel] | None,
    ) -> str:
        sections = [
            "You are operating as a CrewAI custom LLM adapter backed by local Codex CLI.",
            "Respond to the latest user request while preserving prior conversation context.",
        ]

        if tools:
            tool_names = sorted({tool_name for tool in tools for tool_name in tool})
            sections.append(
                "Native function calling is disabled for this adapter. "
                f"Available tool names for textual reference only: {', '.join(tool_names)}."
            )

        if available_functions:
            sections.append(
                "Available function names for textual reference only: "
                f"{', '.join(sorted(available_functions))}."
            )

        if response_model is not None:
            schema = json.dumps(response_model.model_json_schema(), ensure_ascii=True)
            sections.append(f"Return valid JSON matching this schema: {schema}")

        # Codex CLI에는 단일 프롬프트만 전달하므로
        # 대화 이력을 텍스트 transcript로 합친다.
        transcript = []
        for message in messages:
            role = message["role"].upper()
            transcript.append(f"{role}:\n{message['content']}")

        sections.append("\n\n".join(transcript))
        return "\n\n".join(section for section in sections if section.strip())

    def _attach_task_telemetry(
        self,
        task: Any | None,
        *,
        prompt_chars: int | None,
        llm_started_at: str | None,
        llm_finished_at: str | None,
        llm_elapsed_seconds: float | None,
    ) -> None:
        if task is None:
            return
        task._inhouse_llm_telemetry = {
            "prompt_chars": prompt_chars,
            "llm_started_at": llm_started_at,
            "llm_finished_at": llm_finished_at,
            "llm_elapsed_seconds": llm_elapsed_seconds,
        }
