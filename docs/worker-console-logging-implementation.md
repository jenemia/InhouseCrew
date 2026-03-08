# Worker Console Logging Implementation

상태: 구현 완료  
작성일: 2026-03-08

## Goal

`uv run inhouse-crew worker` 실행 시 주문을 집어갔는지, 어떤 task가 진행 중인지
콘솔에서 바로 보이도록 한다.

## Key Decisions

- worker는 startup, order claim, 성공/실패를 stdout에 기록한다.
- task 단위 진행 상태는 기존 `CrewTaskStatusListener` 에 콘솔 로그 훅을 추가해 재사용한다.
- programmatic 호출에서는 로그를 강제하지 않고, CLI 경로에서만 기본 로그를 켠다.

## Done

- worker 시작 시 polling 정보 출력
- order claim / 완료 / 실패 로그 출력
- task `running` / `done` / `failed` 로그 출력
- README 사용 가이드 반영
- worker 로그 테스트 추가

## Verification

- `uv run pytest tests/test_worker.py tests/test_main.py`
- `uv run ruff check src tests`
