# Crew Task Status Tracking Implementation

상태: 구현 완료  
작성일: 2026-03-08

## 1. Goal and Background

이번 변경의 목표는 crew 실행 중 각 agent/task의 진행 상태를 실시간에 가깝게 추적하고,
task가 끝나는 즉시 결과 파일을 남기는 것이다.

공식 CrewAI 문서를 기준으로 아래 기능을 사용한다.

- `TaskStartedEvent`
- `TaskCompletedEvent`
- `TaskFailedEvent`
- `Task.output_file`

핵심 요구:

- run 루트 `status.json`에 전체 task 상태 집계 기록
- 각 task 폴더에 개별 `status.json` 기록
- 상태 값은 `pending`, `running`, `done`, `failed`
- task 완료 시 `result.md`와 optional artifact를 즉시 기록
- 기존 `summary.md` 와 failure artifact 흐름은 유지

## 2. Scope

### In Scope

- 주문 상태 모델에 task 상태 집계 추가
- task workspace에 task-level `status.json` 추가
- CrewAI Event Listener 기반 상태 전환 구현
- `Task.output_file` 기반 task 결과 파일 저장
- 관련 테스트 갱신
- 공식 문서 우선 확인 규칙을 저장소 규칙에 반영

### Out of Scope

- crew process 자체 변경
- task prompt 구조 변경
- UI 추가

## 3. User Scenarios

1. 운영자는 실행 중인 crew에서 어떤 agent/task가 진행 중인지 확인하고 싶다.
2. 운영자는 중간 task가 끝난 즉시 그 결과물을 파일로 열어보고 싶다.
3. 운영자는 실패 시 어느 task까지 완료됐는지 바로 확인하고 싶다.

## 4. Feature List with Priorities

### P0

- run-level `task_statuses` 집계 추가
- task-level `status.json` 추가
- event listener 기반 `running/done/failed` 반영
- `result.md` 및 artifact 즉시 기록

### P1

- 공식 문서 우선 확인 규칙을 `AGENTS.md`에 반영

## 5. Data and Model

추가되는 상태 모델:

- `TaskStatusRecord`
  - `task_id`
  - `agent`
  - `status`
  - `started_at`
  - `finished_at`
  - `result_file`
  - `output_artifact`
  - `failure_file`

변경되는 주문 상태 모델:

- `OrderStatusRecord.task_statuses`

## 6. API / Events / Flow

1. 주문 생성 시 run-level `status.json`에 모든 task를 `pending`으로 초기화한다.
2. worker/CLI 실행 시작 시 각 task 폴더와 task-level `status.json`을 만든다.
3. `run_crew()`는 `crewai_event_bus.scoped_handlers()` 안에서 listener를 등록한다.
4. `TaskStartedEvent`에서 해당 task를 `running`으로 바꾼다.
5. `TaskCompletedEvent`에서 `result.md`를 정리하고 `done`으로 바꾼다.
6. `TaskFailedEvent`에서 해당 task를 `failed`로 바꾼다.
7. 실행 종료 후 run-level `status.json` top status를 `completed` 또는 `failed`로 기록한다.

## 7. Error and Edge Cases

- event listener가 task 이름을 식별하지 못하면 해당 이벤트는 무시한다.
- task 결과 파일이 아직 없으면 listener가 fallback으로 직접 `result.md`를 쓴다.
- 실패 task의 `failure.json`은 기존 프로젝트 레이어가 계속 생성한다.
- event 기반 기록과 최종 정리 루프가 중복으로 실행돼도 결과가 깨지지 않게 idempotent하게 만든다.

## 8. Definition of Done

- run-level `status.json`에서 각 task 상태를 볼 수 있다.
- 각 task 폴더에 `status.json`이 있다.
- task 완료 시 `result.md`가 즉시 생긴다.
- optional artifact도 즉시 생긴다.
- 관련 테스트가 통과한다.

## 9. Constraints

- 공식 CrewAI event system과 `output_file`을 우선 사용한다.
- 수동 편집은 `apply_patch` 로만 수행한다.
- 기존 run-level `queued/running/completed/failed` 의미는 유지한다.

## Ticket Plan

### T1. 상태 모델 및 workspace 확장

상태: Done

- 변경 파일:
  - `src/inhouse_crew/orders.py`
  - `src/inhouse_crew/task_workspace.py`
  - `tests/test_orders.py`
  - `tests/test_task_workspace.py`

### T2. CrewAI Event Listener 및 output_file 연결

상태: Done

- 변경 파일:
  - `src/inhouse_crew/crew_factory.py`
  - `src/inhouse_crew/main.py`
  - `src/inhouse_crew/task_status_listener.py`
  - `tests/fakes.py`
  - `tests/test_main.py`
  - `tests/test_worker.py`

### T3. API 상태 응답 및 문서 규칙 반영

상태: Done

- 변경 파일:
  - `tests/test_api.py`
  - `AGENTS.md`

### T4. 최종 검증

상태: Done

- 검증:
  - `uv run pytest tests/test_orders.py tests/test_main.py tests/test_worker.py tests/test_api.py tests/test_task_workspace.py`
  - `uv run ruff check src tests`
  - `uv run pytest tests/test_crew_factory.py tests/test_persona_loader.py`

## Verification Result

- `TaskStartedEvent`, `TaskCompletedEvent`, `TaskFailedEvent` 기반 상태 전환 구현 완료
- task-level `status.json` 및 run-level `task_statuses` 집계 기록 완료
- `Task.output_file` 기반 `result.md` 즉시 기록 연결 완료
- optional artifact 즉시 복사 기록 완료
- `AGENTS.md` 에 공식 문서 우선 확인 규칙 반영 완료
