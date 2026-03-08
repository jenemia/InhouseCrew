# Goal and Background

workspace run 폴더 아래 task 폴더명이 현재 `task_id` 기준이라, `game_design_team`처럼 agent persona 중심으로 보는 crew에서는 추적성이 떨어진다.
이번 변경은 모든 crew의 새 run에 대해 task 폴더명을 `1.<agent_id>`, `2.<agent_id>` 형식으로 표준화하되, 내부 식별자는 계속 `task_id`를 유지하는 것이 목적이다.

## Scope

### In

- task workspace 폴더명 규칙 추가
- `task_id`와 물리 폴더명 분리
- task status/metadata에 `task_dir_name` 노출
- README 및 테스트 갱신

### Out

- 기존 run 마이그레이션
- `task_id` 키 변경
- replay/resume 식별자 변경

## User Scenarios

1. 새 run에서는 `workspace/runs/<run_id>/1.planner`, `2.developer`처럼 task 순서를 폴더명만 보고 알 수 있다.
2. `status.json`에서 `task_id`는 유지되면서도 실제 폴더명 `task_dir_name`을 확인할 수 있다.
3. 기존 run은 그대로 남고, 새 run부터만 새 규칙이 적용된다.

## Data and Model

- `TaskWorkspace.create_task(..., task_dir_name: str | None = None)`
- `TaskContext.task_dir_name: str`
- `TaskStatusRecord.task_dir_name: str | None`
- task `metadata.json` / `status.json`
  - `task_dir_name`

## API / Flow

1. `run_crew()`가 spec task 순서와 agent id로 `task_dir_name`을 계산한다.
2. `TaskWorkspace.create_task()`는 `task_id`는 내부 식별자로 유지하고, 실제 폴더는 `task_dir_name`으로 만든다.
3. run-level `task_statuses` key는 계속 `task_id`를 사용한다.
4. 상태/결과 경로는 새 task 폴더 경로를 가리킨다.

## Error and Edge Cases

- `task_dir_name`이 비어 있으면 기존 `task_id` fallback
- 같은 agent가 여러 번 등장해도 순번으로 충돌 회피
- 기존 status 파일에서 `task_dir_name`이 없어도 읽을 수 있어야 함

## Definition of Done

- 새 run task 폴더명이 `1.<agent_id>` 형식으로 생성된다.
- `task_statuses` key는 그대로 `task_id`다.
- `task_dir_name`이 task status/metadata에 기록된다.
- 관련 테스트와 ruff가 통과한다.

## Tickets

### T1. Workspace Naming Support

- `TaskWorkspace`와 `TaskContext`에 `task_dir_name`을 추가한다.
- `create_task()`가 optional `task_dir_name`을 받아 실제 폴더명으로 사용한다.

### T2. Runtime Mapping

- `run_crew()`와 queued status 초기화가 순번 기반 `task_dir_name`을 계산한다.
- 상태/메타데이터에 `task_dir_name`을 기록한다.

### T3. Tests and Docs

- `tests/test_task_workspace.py`, `tests/test_orders.py`, `tests/test_main.py`, `tests/test_worker.py`, `tests/test_api.py`
- README에 새 naming 규칙 설명 추가

## Constraints

- 내부 시스템 식별자는 계속 `task_id`
- 새 run부터만 적용
- 수정은 `apply_patch`만 사용
