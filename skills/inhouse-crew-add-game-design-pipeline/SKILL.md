---
name: inhouse-crew-add-game-design-pipeline
description: Add or update InhouseCrew game design pipeline crews under `configs/crews/*.yaml` and keep related game design personas, tests, docs, and local agent rules synchronized. Use when Codex needs to create, revise, or review a multi-step game design crew such as a concept to fantasy to innovation to market to synthesis pipeline in this repository.
---

# Inhouse Crew Add Game Design Pipeline

## Overview

Keep game design pipeline crews config-driven and synchronized with their persona bundle, tests, docs, and local repository rules.
When the user asks for a multi-agent game design workflow, define the crew in YAML, add only the missing personas, and update verification/docs together.

## Workflow

1. Read the existing game design personas under `configs/agents/` and current crew examples under `configs/crews/` first.
2. Create or update one `docs/*-implementation.md` document before changing production configs.
3. Prefer sequential crews unless the user explicitly asks for another process model.
4. Keep each task owned by exactly one persona and give every task a stable artifact file name.
5. Add only the missing personas required by the pipeline. Do not rewrite unrelated personas.
6. Keep the implementation config-driven. Do not add wrapper modules under `src/inhouse_crew/domain/` unless the user explicitly asks.
7. Put stable project background into `knowledge/<crew_id>/project_brief.md` when the crew needs reusable default context.
8. Use `memory: true` only when the crew benefits from cross-run accumulation. Default to off for new crews.
9. Update `tests/test_persona_loader.py` and `tests/test_crew_factory.py` whenever the sample registry or crew catalog changes.
10. Keep `README.md` to exactly one persona example block. Update sample crew mentions without adding more persona examples.
11. Update `AGENTS.md` so future sessions know when to use this skill.
12. Validate the new skill and run the relevant pytest targets after config changes.
13. Store crew-specific personas under `configs/agents/<crew_id>/` and leave shared personas at the `configs/agents/` root.

## Editing Rules

- Keep crew ids in `snake_case` and file names aligned with the id.
- Prefer short task ids that describe the stage outcome, not the implementation detail.
- Include `오늘 날짜는 {current_date}다.` only when the task meaning depends on temporal context.
- Make the final synthesis task explicit when the crew needs a single final design conclusion.
- If stable project context is required, prefer crew-level knowledge files over repeating long default prompts.
- If the user provides an agent id with a typo, normalize to the closest existing repository id and record that choice in the implementation doc.
- Avoid duplicate persona ids across the `configs/agents/` tree. Treat them as a registry error rather than relying on overwrite order.

## Reference

- Use [references/crew-template.md](references/crew-template.md) for the expected crew layout.
- Use [references/persona-bundle-guidelines.md](references/persona-bundle-guidelines.md) for deciding when a new lead persona is required.
