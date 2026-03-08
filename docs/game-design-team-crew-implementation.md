# Game Design Team Crew Implementation

상태: 구현 완료  
작성일: 2026-03-07

검증 결과:

- `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py` 통과
- `uv run python /Users/sean/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/inhouse-crew-add-game-design-pipeline` 통과
- `uv run inhouse-crew run --crew-id game_design_team --input "도시 하늘 위를 배달하며 세력 균형을 흔드는 액션 게임을 기획해줘"` 실행 시 `design_unique_hook` 단계에서 `CodexTimeoutError` 발생
- 실패 run 디렉터리: `workspace/runs/20260307T144741Z-game_design_team-9ec78f1d`

## 1. Goal and Background

이번 변경의 목표는 시니어 게임 디자이너 팀이 순차적으로 게임 시스템과 콘텐츠를 기획하고
방향성을 결정할 수 있는 `game_design_team` crew를 추가하는 것이다.

팀 진행 순서는 다음과 같다.

1. `game_concept_generator`
2. `game_fantasy_designer`
3. `game_innovation_designer`
4. `game_market_validator`
5. `game_design_director`

마지막 단계는 앞선 4개 산출물을 종합해 최종 게임 방향성 문서를 만든다.

같은 작업을 반복할 수 있도록 저장소 내부 로컬 skill도 함께 추가한다.

## 2. Scope

### In Scope

- `game_design_director` persona 추가
- `game_design_team` crew 추가
- 관련 테스트 갱신
- README 샘플 crew 목록 갱신
- 로컬 skill 추가 및 `AGENTS.md` 트리거 갱신

### Out of Scope

- `src/inhouse_crew/domain/` wrapper 추가
- 런타임 코드 변경
- README persona 예제 정책 변경

## 3. User Scenarios

1. 운영자는 여러 game design persona를 순차적으로 실행하는 crew를 바로 사용하고 싶다.
2. 운영자는 각 단계 산출물과 최종 종합 문서를 모두 run artifact로 남기고 싶다.
3. 운영자는 이후 유사한 game design pipeline 요청을 로컬 skill 규칙으로 반복 처리하고 싶다.

## 4. Feature List with Priorities

### P0

- `game_design_team` crew 추가
- `game_design_director` persona 추가
- registry 및 crew factory 테스트 갱신

### P1

- 로컬 skill 추가
- `AGENTS.md` 트리거 규칙 갱신
- README 샘플 crew 목록 갱신

## 5. Data and Model

추가되는 config interface:

- `configs/agents/game_design_director.yaml`
- `configs/crews/game_design_team.yaml`

`game_design_team` task artifact:

- `concept.md`
- `fantasy.md`
- `innovation.md`
- `market_validation.md`
- `game_design_direction.md`

## 6. API / Events / Flow

1. `load_registry(Path("configs"))` 가 새 agent/crew YAML을 읽는다.
2. `CrewFactory.create_crew("game_design_team")` 가 config만으로 crew를 조립한다.
3. sequential process에 따라 5개 task가 순서대로 실행된다.
4. 각 task 결과는 artifact로 저장되고, 마지막 task가 최종 방향성 문서를 산출한다.

## 7. UI / UX

UI 변경은 없다. 출력 경험은 단계별 기획 문서와 최종 종합 문서 구분에 집중한다.

## 8. Error and Edge Cases

- task agent id가 잘못되면 crew 조립 실패
- 새 crew를 추가했는데 테스트 기대값을 갱신하지 않으면 registry 테스트 실패
- README는 persona 예제 1개 정책을 유지해야 하므로 crew 소개만 갱신해야 함
- smoke run은 로컬 Codex CLI 상태에 따라 실패할 수 있음

## 9. Definition of Done

- `game_design_director` persona가 추가된다
- `game_design_team` crew가 추가된다
- 관련 테스트가 통과한다
- 로컬 skill이 검증을 통과한다
- README와 `AGENTS.md`가 새 crew/skill을 반영한다

## 10. Constraints

- config-driven 방식만 사용한다
- `src/inhouse_crew/domain/` 에 wrapper를 추가하지 않는다
- 수동 편집은 `apply_patch` 로만 수행한다
- README persona 예제는 1개만 유지한다

## Ticket Plan

### T1. Lead Persona 및 Crew Config 추가

상태: Completed (2026-03-07)

- 목적: 새 synthesis persona와 `game_design_team` crew를 추가
- 변경 파일:
  - `configs/agents/game_design_director.yaml`
  - `configs/crews/game_design_team.yaml`
- 검증:
  - `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py`

### T2. 테스트 및 문서 갱신

상태: Completed (2026-03-07)

- 목적: registry/crew factory 테스트와 README 상태 문서 갱신
- 변경 파일:
  - `tests/test_persona_loader.py`
  - `tests/test_crew_factory.py`
  - `README.md`
- 검증:
  - `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py`

### T3. 로컬 Skill 및 AGENTS 규칙 추가

상태: Completed (2026-03-07)

- 목적: crew 생성 과정을 재사용할 저장소 내부 skill 추가
- 변경 파일:
  - `skills/inhouse-crew-add-game-design-pipeline/SKILL.md`
  - `skills/inhouse-crew-add-game-design-pipeline/agents/openai.yaml`
  - `skills/inhouse-crew-add-game-design-pipeline/references/*.md`
  - `AGENTS.md`
- 검증:
  - `uv run python /Users/sean/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/inhouse-crew-add-game-design-pipeline`

### T4. 스모크 검증

상태: Completed with timeout finding (2026-03-07)

- 목적: 새 crew가 실제 실행 가능한지 확인
- 검증:
  - `uv run inhouse-crew run --crew-id game_design_team --input "<짧은 게임 아이디어 요청>"`
