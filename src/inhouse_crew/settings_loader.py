from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_embedder() -> dict[str, Any]:
    return {
        "provider": "ollama",
        "config": {
            "url": "http://localhost:11434/api/embeddings",
            "model_name": "qwen3-embedding:4b",
        },
    }


class AppSettings(BaseSettings):
    # 실행 시점 설정은 환경 변수 override를 받을 수 있어야 하므로 BaseSettings를 사용한다.
    model_config = SettingsConfigDict(
        env_prefix="INHOUSE_CREW_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    workspace_root: Path = Path("workspace/runs")
    default_llm: str = "codex-local-oauth"
    codex_command: str = "codex"
    codex_model: str | None = None
    timeout_seconds: int = 120
    retry_count: int = 1
    embedder: dict[str, Any] | None = Field(default_factory=_default_embedder)
    crewai_storage_root: Path = Path("workspace/crewai_storage")


class SettingsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_root: Path = Path("workspace/runs")
    default_llm: str = "codex-local-oauth"
    codex_command: str = "codex"
    codex_model: str | None = None
    timeout_seconds: int = 120
    retry_count: int = 1
    embedder: dict[str, Any] | None = Field(default_factory=_default_embedder)
    crewai_storage_root: Path = Path("workspace/crewai_storage")


def _load_yaml_dict(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping at {path}, got {type(data).__name__}")
    return data


def _load_env_overrides(env_file: Path | None) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    env_data = dotenv_values(env_file) if env_file is not None and env_file.exists() else {}

    # YAML 기본값 위에 .env, 그 위에 프로세스 환경변수를 덮어쓰는 우선순위를 유지한다.
    for field_name in SettingsFile.model_fields:
        env_name = f"INHOUSE_CREW_{field_name.upper()}"
        if env_name in env_data and env_data[env_name] is not None:
            overrides[field_name] = _parse_env_override(field_name, env_data[env_name])
        if env_name in os.environ:
            overrides[field_name] = _parse_env_override(field_name, os.environ[env_name])

    return overrides


def _parse_env_override(field_name: str, raw_value: Any) -> Any:
    if field_name == "embedder" and isinstance(raw_value, str):
        parsed = yaml.safe_load(raw_value)
        if parsed is None:
            return None
        if not isinstance(parsed, dict):
            raise ValueError("INHOUSE_CREW_EMBEDDER must be a JSON/YAML object or null")
        return parsed
    return raw_value


def load_settings(settings_path: Path, env_file: Path | None = None) -> AppSettings:
    file_settings = SettingsFile.model_validate(_load_yaml_dict(settings_path))
    merged_settings = file_settings.model_dump()
    merged_settings.update(_load_env_overrides(env_file))
    # 최종 검증은 AppSettings 한 번으로 통일해 타입 변환 경로를 단순화한다.
    return AppSettings.model_validate(merged_settings)


__all__ = ["AppSettings", "SettingsFile", "load_settings"]
