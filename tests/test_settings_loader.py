from __future__ import annotations

from pathlib import Path

from inhouse_crew.settings_loader import load_settings


def test_load_settings_reads_yaml_defaults() -> None:
    settings = load_settings(Path("configs/settings.yaml"))

    assert settings.workspace_root == Path("workspace/runs")
    assert settings.crewai_storage_root == Path("workspace/crewai_storage")
    assert settings.default_llm == "codex-local-oauth"
    assert settings.codex_command == "codex"
    assert settings.embedder == {
        "provider": "ollama",
        "config": {
            "url": "http://localhost:11434/api/embeddings",
            "model_name": "qwen3-embedding:4b",
        },
    }


def test_load_settings_allows_env_override(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "INHOUSE_CREW_TIMEOUT_SECONDS=45\n"
        "INHOUSE_CREW_CREWAI_STORAGE_ROOT=workspace/custom_crewai_storage\n"
        'INHOUSE_CREW_EMBEDDER={"provider":"ollama","config":{"url":"http://localhost:11434/api/embeddings","model_name":"mxbai-embed-large"}}\n',
        encoding="utf-8",
    )

    settings = load_settings(Path("configs/settings.yaml"), env_file=env_file)

    assert settings.timeout_seconds == 45
    assert settings.crewai_storage_root == Path("workspace/custom_crewai_storage")
    assert settings.embedder == {
        "provider": "ollama",
        "config": {
            "url": "http://localhost:11434/api/embeddings",
            "model_name": "mxbai-embed-large",
        },
    }
