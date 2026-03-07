from __future__ import annotations

from pathlib import Path

from inhouse_crew.settings_loader import load_settings


def test_load_settings_reads_yaml_defaults() -> None:
    settings = load_settings(Path("configs/settings.yaml"))

    assert settings.workspace_root == Path("workspace/runs")
    assert settings.default_llm == "codex-local-oauth"
    assert settings.codex_command == "codex"


def test_load_settings_allows_env_override(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("INHOUSE_CREW_TIMEOUT_SECONDS=45\n", encoding="utf-8")

    settings = load_settings(Path("configs/settings.yaml"), env_file=env_file)

    assert settings.timeout_seconds == 45
