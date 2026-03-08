## Local Skills

- `inhouse-crew-add-agent-persona`: InhouseCrew의 agent persona를 `configs/agents/*.yaml` 아래에 추가, 수정, 교체, 검토할 때 사용한다. `tests/test_persona_loader.py` 동기화와 `README.md` 의 persona 예제 1개 정책을 함께 강제한다. (file: `skills/inhouse-crew-add-agent-persona/SKILL.md`)
- `inhouse-crew-add-game-design-pipeline`: InhouseCrew의 multi-agent game design crew를 `configs/crews/*.yaml` 아래에 추가, 수정, 검토할 때 사용한다. 관련 persona bundle, `tests/test_persona_loader.py`, `tests/test_crew_factory.py`, `README.md`, `AGENTS.md` 동기화를 함께 강제한다. (file: `skills/inhouse-crew-add-game-design-pipeline/SKILL.md`)

## How to Use Local Skills

- 사용자가 agent persona 추가/수정/리뷰를 요청하면 먼저 `skills/inhouse-crew-add-agent-persona/SKILL.md` 를 읽고 그 절차를 따른다.
- 사용자가 `game design team crew`, `game design pipeline`, `concept/fantasy/innovation/market validator 묶음 crew` 추가 또는 수정을 요청하면 먼저 `skills/inhouse-crew-add-game-design-pipeline/SKILL.md` 를 읽고 그 절차를 따른다.
- persona 작업에서는 `configs/crews/*.yaml` 를 기본적으로 수정하지 않는다. crew 변경은 사용자가 명시적으로 요청한 경우에만 수행한다.
- 구현성 변경 요청이면 production 파일을 수정하기 전에 관련 `docs/*-implementation.md` 문서를 먼저 만들거나 갱신한다.
