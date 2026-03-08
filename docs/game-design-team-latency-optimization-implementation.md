# Goal and Background

`game_design_team` crew는 5-agent sequential 구조를 유지하면서도 task별 지연을 줄여야 한다.
현재 병목은 CrewAI의 기본 sequential context relay, persistent knowledge 오염, 긴 최종 프롬프트가 겹쳐 발생한다.
이번 변경은 공식 CrewAI 패턴을 따라 `Task.context`, knowledge reset, task telemetry를 도입해 first-run latency를 낮추고 원인 추적 근거를 남기는 데 집중한다.

## Scope

### In

- `CrewTaskSpec.context_tasks` 추가
- `game_design_team` selective context 적용
- knowledge source signature 기반 자동 reset
- task status telemetry 추가
- README 운영 가이드 갱신
- 회귀 테스트 보강

### Out

- hierarchical 전환
- replay/resume 구현
- Codex session reuse
- intermediate artifact 요약/상세 이중화

## User Scenarios

1. `game_design_team` 실행 시 불필요한 이전 산출물 누적 없이 필요한 결과만 다음 task에 전달된다.
2. knowledge 파일을 수정하면 다음 실행에서 stale knowledge가 재사용되지 않는다.
3. run/task 상태 파일만 보고 prompt 크기와 LLM 소요 시간을 확인할 수 있다.

## Feature List

### P0

- task 단위 explicit context graph 지원
- knowledge source 변경 시 자동 reset
- task status에 prompt/LLM elapsed telemetry 기록

### P1

- README에 automatic knowledge reset 운영 가이드 반영

## Data and Model

- `CrewTaskSpec`
  - `context_tasks: list[str] = []`
- `TaskStatusRecord`
  - `context_task_ids: list[str]`
  - `prompt_chars: int | None`
  - `llm_started_at: str | None`
  - `llm_finished_at: str | None`
  - `llm_elapsed_seconds: float | None`
  - `knowledge_reset_applied: bool | None`
- `CodexRunResult` / `CodexFailureDetails`
  - prompt 길이와 wall-clock telemetry 포함

## API / Flow

1. `run_crew()`가 task workspace를 만든다.
2. `CrewFactory.create_crew()`가 `Task.context`와 knowledge reset 여부를 포함한 crew를 조립한다.
3. `CrewTaskStatusListener`가 completion/failure 시 task telemetry를 status에 기록한다.
4. run/task status는 기존 계약을 유지하되 telemetry 필드를 추가한다.

## Error and Edge Cases

- `context_tasks`가 존재하지 않는 task를 참조하면 `CrewFactoryError`
- `context_tasks`가 현재 task 자신 또는 뒤 task를 참조하면 `CrewFactoryError`
- knowledge signature sidecar가 없으면 안전하게 reset 후 새 signature를 기록
- telemetry가 없는 task는 해당 필드를 `null`로 유지

## Definition of Done

- `game_design_team`의 task graph가 explicit context로 동작한다.
- knowledge 파일 변경 후 stale knowledge가 재사용되지 않는다.
- task status에 telemetry가 기록된다.
- 관련 pytest와 ruff가 통과한다.

## Constraints

- 기존 5-agent sequential 구조 유지
- 생성 LLM은 로컬 Codex 유지
- `memory`는 계속 비활성화
- 문서/코드 수정은 `apply_patch`만 사용

## Tickets

### T1. Crew Spec and Context Graph

- Purpose: `CrewTaskSpec.context_tasks`와 `game_design_team` selective context를 도입한다.
- Changed files:
  - `src/inhouse_crew/persona_loader.py`
  - `src/inhouse_crew/crew_factory.py`
  - `configs/crews/game_design_team.yaml`
- Acceptance criteria:
  - YAML에서 `context_tasks`를 읽을 수 있다.
  - `Task.context`가 지정된 task에만 연결된다.
  - 잘못된 context graph는 조립 단계에서 실패한다.

### T2. Knowledge Freshness

- Purpose: knowledge source signature 기반 자동 reset을 도입한다.
- Changed files:
  - `src/inhouse_crew/crew_factory.py`
  - `README.md`
- Acceptance criteria:
  - knowledge source 변경 시 `Knowledge.reset()`이 호출된다.
  - 변경이 없으면 reset 없이 재사용한다.
  - sidecar metadata가 `workspace/crewai_storage/knowledge` 아래 기록된다.

### T3. Task Telemetry

- Purpose: prompt/LLM timing telemetry를 task status에 기록한다.
- Changed files:
  - `src/inhouse_crew/llms/codex_runner.py`
  - `src/inhouse_crew/llms/codex_cli_llm.py`
  - `src/inhouse_crew/orders.py`
  - `src/inhouse_crew/main.py`
  - `src/inhouse_crew/task_workspace.py`
  - `src/inhouse_crew/task_status_listener.py`
- Acceptance criteria:
  - success/failure task 모두 telemetry 필드를 가진다.
  - 기존 status/result 기록 동작은 유지된다.

### T4. Tests and Verification

- Purpose: selective context, knowledge reset, telemetry 회귀를 보장한다.
- Changed files:
  - `tests/test_persona_loader.py`
  - `tests/test_crew_factory.py`
  - `tests/test_main.py`
  - `tests/test_orders.py`
  - `tests/test_task_workspace.py`
  - `tests/fakes.py`
- Verification:
  - `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py tests/test_main.py tests/test_orders.py tests/test_task_workspace.py`
  - `uv run ruff check src tests`
