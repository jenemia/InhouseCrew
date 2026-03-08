---
name: inhouse-crew-add-agent-persona
description: Add or update InhouseCrew agent personas under `configs/agents/**/*.yaml` and keep repository rules in sync. Use when Codex needs to create, revise, replace, or review an agent persona in this repository, especially if `tests/test_persona_loader.py` and the single-example persona policy in `README.md` must be updated together.
---

# Inhouse Crew Add Agent Persona

## Overview

Keep agent persona changes in this repository small, consistent, and synchronized.
When the user asks for a new or revised persona, update the persona YAML, sync the registry test, and preserve the README single-example rule.

## Workflow

1. Read `configs/agents/planner.yaml`, `configs/agents/developer.yaml`, and `configs/agents/reviewer.yaml` first to match tone, field order, and brevity.
2. Add or update exactly one persona file unless the user explicitly asks for a batch change.
3. Place shared personas in `configs/agents/` and crew-scoped personas in `configs/agents/<crew_id>/`.
4. Keep persona ids in `snake_case` and compatible with `AgentPersona` in `src/inhouse_crew/persona_loader.py`.
5. Update `tests/test_persona_loader.py` whenever the set of sample agents changes.
6. Keep `README.md` to exactly one persona file example. Replace the existing example instead of adding another.
7. Do not modify `configs/crews/*.yaml` unless the user explicitly asks for crew changes.
8. If the request is implementation work, create or update a `docs/*-implementation.md` spec before editing production files.
9. Run `uv run pytest tests/test_persona_loader.py` after changing persona configs or registry expectations.

## Editing Rules

- Preserve the YAML field order used by existing personas.
- Keep prose Korean-first, but keep English role names when they are part of the requested identity.
- Prefer `tools: []` unless the persona clearly needs repository I/O tools.
- Keep backstory and rules concise. Avoid feature-complete system design inside persona text.
- If README needs a persona example refresh, use the most relevant current persona and keep it as the only example block.
- Avoid duplicate agent ids across folders. Loader treats them as an error.

## Reference

See [references/persona-template.md](references/persona-template.md) for the expected file shape and a quick checklist.
