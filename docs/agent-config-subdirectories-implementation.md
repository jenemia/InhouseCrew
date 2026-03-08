# Agent Config Subdirectories Implementation

## Goal and Background

현재 agent persona는 `configs/agents/*.yaml` 평면 구조만 지원한다.
crew 수가 늘어나면 도메인별 persona를 함께 관리하기 어렵기 때문에,
`configs/agents/<crew_id>/` 같은 하위 폴더 구조를 지원해 crew-scoped persona를 묶어둘 수 있어야 한다.

이번 변경은 `game_design_team` 관련 persona를 실제로 하위 폴더로 이동하고,
앞으로의 persona/crew 추가 작업도 같은 규칙을 따르도록 loader, 테스트, README, AGENTS, local skill 문서를 함께 정리하는 것을 목표로 한다.

## Scope

### In

- `configs/agents/**/*.yaml` 재귀 로딩 지원
- agent `id` 중복 감지와 명시적 에러 처리
- `game_design_team` persona 5종을 `configs/agents/game_design_team/` 으로 이동
- active guidance 문서와 local skill 규칙을 새 폴더 정책에 맞게 갱신
- 관련 pytest 갱신 및 회귀 검증

### Out

- `configs/crews/` 하위 폴더 지원
- crew YAML schema 변경
- 다른 도메인 persona의 대규모 재분류
- 과거 구현 문서 전수 수정

## User Scenarios

1. 운영자는 `game_design_team` 관련 persona를 한 폴더에서 묶어 보고 수정할 수 있다.
2. 새 crew 전용 persona를 추가할 때 `configs/agents/<crew_id>/` 아래에 배치해 구조를 일관되게 유지할 수 있다.
3. shared persona는 계속 `configs/agents/` 루트에 두고 여러 crew에서 재사용할 수 있다.
4. 서로 다른 파일에 같은 agent `id` 가 생기면 로더가 즉시 실패해 잘못된 registry 상태로 실행되지 않는다.

## Feature List

### P0

- agent persona loader가 `configs/agents/**/*.yaml` 를 deterministic order로 읽는다.
- duplicate agent id 발견 시 충돌 파일 경로를 포함한 `ValueError` 를 발생시킨다.
- `game_design_team` persona 파일이 새 하위 폴더에서도 기존 crew id 참조로 정상 동작한다.
- README, AGENTS, local skill이 새 배치 규칙을 명시한다.

### P1

- 테스트가 nested persona 발견과 duplicate id 실패를 회귀 검증한다.

## Data and Model

- `AgentPersona`, `CrewSpec`, `CrewTaskSpec`, `CrewOutputPolicy` schema는 변경하지 않는다.
- crew YAML의 `agents` 필드는 계속 agent `id` 문자열 목록만 사용한다.
- 경로 규칙만 변경한다.
  - shared persona: `configs/agents/<agent_id>.yaml`
  - crew-scoped persona: `configs/agents/<crew_id>/<agent_id>.yaml`

## API / Events / Flow

1. `load_registry(Path("configs"))` 호출
2. `load_agent_personas(config_root / "agents")` 가 `**/*.yaml` 재귀 순회
3. 각 파일을 `load_agent_persona()` 로 검증
4. 이미 등록된 `persona.id` 가 나오면 기존 파일 경로와 신규 파일 경로를 함께 담아 실패
5. `load_crew_specs(config_root / "crews")` 는 기존처럼 `*.yaml` 만 로딩
6. `CrewFactory` 와 주문 생성 로직은 기존 `id` 기반 참조를 그대로 사용

## UI / UX

해당 없음.

## Error and Edge Cases

- nested 폴더와 루트 파일이 같은 `id` 를 가지면 실행 전에 실패해야 한다.
- 정렬 순서는 파일 경로 기준 deterministic 해야 테스트와 동작이 일관된다.
- `configs/crews/*.yaml` 는 재귀화하지 않아 기존 crew 배치 정책을 유지한다.
- user가 수정 중인 `knowledge/` 나 `todo/` 등의 unrelated working tree 변경은 건드리지 않는다.

## Definition of Done

- `game_design_team` persona 5종이 `configs/agents/game_design_team/` 아래로 이동한다.
- `load_registry()` 가 nested agent 파일을 읽고 기존 crew 생성이 그대로 통과한다.
- duplicate agent id 테스트가 추가된다.
- README, AGENTS, 두 local skill 문서가 새 폴더 정책을 설명한다.
- `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py tests/test_orders.py -q` 가 통과한다.

## Constraints

- production 파일 수정 전에 이 문서를 먼저 추가한다.
- public interface는 `agent id` 기반 참조를 유지한다.
- crew config는 flat 유지, agent config만 tree 구조를 허용한다.
- historical docs는 현재 작업 지침이 아닌 한 대량 수정하지 않는다.
- 수동 파일 수정은 patch 기반으로 수행한다.

## Tickets

### T1. Spec and Loader Rules

- Status: Completed
- Purpose: 재귀 로딩과 duplicate 정책을 loader에 반영한다.
- Changed files:
  - `docs/agent-config-subdirectories-implementation.md`
  - `src/inhouse_crew/persona_loader.py`
- Implementation details:
  - agent persona 파일 탐색을 `rglob("*.yaml")` 기반으로 바꾼다.
  - duplicate id 충돌 시 두 파일 경로가 포함된 예외를 추가한다.
- Acceptance criteria:
  - nested agent file이 registry에 포함된다.
  - duplicate id는 즉시 실패한다.
- Verification:
  - `uv run pytest tests/test_persona_loader.py -q`

### T2. Persona Migration

- Status: Completed
- Purpose: `game_design_team` persona bundle을 하위 폴더로 이동한다.
- Changed files:
  - `configs/agents/game_design_team/*.yaml`
- Implementation details:
  - game design 전용 5개 persona를 새 폴더로 재배치한다.
  - crew YAML의 agent id 참조는 유지한다.
- Acceptance criteria:
  - game design persona 파일이 새 경로에 존재한다.
  - crew registry와 factory 동작이 유지된다.
- Verification:
  - `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py -q`

### T3. Tests and Regression Coverage

- Status: Completed
- Purpose: nested discovery와 duplicate id 실패를 테스트로 고정한다.
- Changed files:
  - `tests/test_persona_loader.py`
- Implementation details:
  - nested persona 경로를 검증하는 assertion을 추가한다.
  - duplicate id 충돌용 tmp config fixture 테스트를 추가한다.
- Acceptance criteria:
  - 신규 테스트가 의도한 실패/성공을 검증한다.
- Verification:
  - `uv run pytest tests/test_persona_loader.py -q`

### T4. Active Guidance Sync

- Status: Completed
- Purpose: 운영 문서와 skill 규칙을 새 폴더 정책과 맞춘다.
- Changed files:
  - `README.md`
  - `AGENTS.md`
  - `skills/inhouse-crew-add-agent-persona/SKILL.md`
  - `skills/inhouse-crew-add-game-design-pipeline/SKILL.md`
- Implementation details:
  - flat `configs/agents/*.yaml` 표현을 recursive agent-tree 표현으로 바꾼다.
  - shared persona와 crew-scoped persona 배치 규칙을 문서화한다.
- Acceptance criteria:
  - 향후 세션이 새 agent 배치 규칙을 문서만 보고 따를 수 있다.
- Verification:
  - 관련 문서 diff 검토

### T5. End-to-End Verification

- Status: Completed
- Purpose: loader, crew factory, order flow 회귀를 최종 확인한다.
- Changed files:
  - 없음
- Implementation details:
  - 지정된 pytest 타깃을 실행한다.
- Acceptance criteria:
  - 모든 지정 테스트가 통과한다.
- Verification:
  - `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py tests/test_orders.py -q`
  - Result: `15 passed`
