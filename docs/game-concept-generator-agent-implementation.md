# Game Concept Generator Persona and Skill Implementation

상태: Completed  
전체 상태: 구현 및 검증 완료  
작성일: 2026-03-07

검증 결과:

- `uv run pytest tests/test_persona_loader.py`
- `uv run python /Users/sean/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/inhouse-crew-add-agent-persona`

## 1. Goal and Background

현재 프로젝트는 `configs/agents/*.yaml` 에 에이전트 페르소나를 YAML 데이터로 정의하고, `configs/crews/*.yaml` 가 이를 참조하는 구조를 사용한다.  
이번 요청의 목표는 다음 2가지를 기존 구조와 맞게 정리하는 것이다.

- `Game Concept Generator` 페르소나 추가
- 이후 같은 작업을 압축해 반복할 수 있도록 InhouseCrew 전용 persona 추가 skill 정리

사용자가 제공한 원문 요구는 다음에 집중한다.

- 새로운 게임 아이디어를 만드는 창의적인 게임 디렉터 페르소나
- 산출물은 게임 컨셉 초안
- 반드시 포함할 요소:
  - 장르
  - 핵심 테마
  - 기본적인 게임 플레이 루프
  - 플레이어 동기
- 독창성과 명확성 중시
- 초기 단계에서는 과도하게 복잡한 시스템 설계 금지

추가 요구사항:

- `README.md` 에는 persona 파일 예시를 1개만 유지
- 나머지 persona 설명은 삭제하거나 일반화
- 다음부터는 같은 요청을 skill 기반으로 처리할 수 있어야 함

## 2. Scope

### In Scope

- `configs/agents/` 아래 새 agent persona YAML 추가
- 기존 agent 파일 구조와 필드 규칙을 그대로 준수
- 레지스트리 로딩 테스트 갱신
- `README.md` 를 persona 예제 1개 중심으로 압축
- InhouseCrew용 persona 추가 skill 생성
- skill 검증 및 기본 메타데이터 정리

### Out of Scope

- 새 crew 추가
- 기존 crew task 재배선
- 런타임 로직 변경
- 게임 디자인 템플릿 엔진이나 별도 후처리 로직 추가
- persona 생성 자동화 CLI 자체 구현

## 3. User Scenarios

1. 운영자는 설정 파일만 추가해 새로운 창의 기획용 agent를 등록하고 싶다.
2. 운영자는 이후 별도 crew에서 이 agent id를 참조해 게임 컨셉 발상 작업에 재사용하고 싶다.
3. 운영자는 페르소나 문구가 한국어/영어 혼합 입력이어도 일관된 출력 방향을 갖기를 원한다.
4. 운영자는 다음부터 같은 종류의 요청이 오면 별도 설명 없이 재사용 가능한 skill 지침으로 처리되길 원한다.
5. 운영자는 README에서 persona 구조를 볼 때 예제는 하나만 보고 전체 패턴을 이해하길 원한다.

## 4. Feature List with Priorities

### P0

- `game_concept_generator` agent persona 추가
- 기존 schema와 호환되는 YAML 유지
- 로더 테스트 기대값 갱신
- persona 추가용 skill 생성

### P1

- README에 persona 예제 1개만 남기고 설명 압축
- skill 메타데이터 정리

## 5. Data and Model

새 agent persona는 기존 `AgentPersona` 스키마를 그대로 사용한다.

- `id`: `game_concept_generator`
- `role`: 게임 컨셉 발상 역할을 직접 드러내는 이름
- `goal`: 강력한 출발점이 되는 게임 컨셉 생성
- `backstory`: 창의적 게임 디렉터 관점의 정체성
- `rules`: 출력 포함 요소와 금지 사항을 명시
- `allow_delegation`: `false`
- `verbose`: `true`
- `llm`: `codex-local-oauth`
- `tools`: 기본적으로 빈 목록

새 skill의 권장 위치와 구성:

- 위치 권장안: `skills/<skill-name>/`
- 이유: 저장소 내부 규칙으로 버전 관리하고, 프로젝트 문맥과 함께 유지하기 위해서
- 최소 구성:
  - `SKILL.md`
  - 필요 시 `references/agent-template.md`

추가 연결 규칙:

- 루트 `AGENTS.md` 에 로컬 skill 목록과 트리거 조건을 명시
- 다음 세션의 Codex가 저장소 규칙을 읽고 해당 skill을 우선 사용하도록 유도

skill이 다룰 반복 작업 범위:

- agent persona YAML 추가
- 관련 테스트 기대값 갱신
- README의 단일 예제 정책 유지
- 기존 구조와 톤에 맞는 값 선택

## 6. API / Events / Flow

persona 로딩 흐름은 기존과 같다.

1. `load_registry(Path("configs"))` 가 `configs/agents/*.yaml` 를 순회한다.
2. 새 YAML이 `AgentPersona` schema 검증을 통과하면 registry에 등록된다.
3. 이후 어떤 crew든 `agents:` 목록과 `tasks[].agent` 에 `game_concept_generator` 를 참조해 사용할 수 있다.

skill 사용 흐름은 다음을 목표로 한다.

1. 사용자가 새 persona 추가를 요청한다.
2. Codex가 InhouseCrew persona 추가 skill을 트리거한다.
3. skill이 저장소 구조 확인, persona YAML 작성, 테스트 갱신, README 단일 예제 정책 반영 순서를 강제한다.
4. 필요 시 예시 템플릿을 참고해 일관된 persona 문구를 만든다.

## 7. UI / UX

UI는 없고, persona 문구 자체가 사용자 경험을 결정한다.

중점:

- 짧고 명확한 컨셉 생성 지시
- 과도한 시스템 설계 억제
- 출력 초점이 컨셉 초안에 머물도록 유도
- README는 persona 파일 예시 1개만 보여주고 나머지는 구조 설명으로 대체

## 8. Error and Edge Cases

- YAML 필드명이 기존 schema와 다르면 로딩 실패
- 지나치게 장황한 backstory는 다른 agent들과 톤이 어긋날 수 있음
- rules에 요구사항을 과하게 중복하면 프롬프트가 불필요하게 비대해질 수 있음
- persona만 추가하고 crew를 연결하지 않으면 즉시 실행 가능한 샘플은 생기지 않음
- 저장소 내부 skill만 두고 `AGENTS.md` 에 연결하지 않으면 다음 세션에서 사용 규칙이 약해질 수 있음
- README에 여러 persona 예시를 넣으면 실제 요청과 무관한 유지보수 부담이 커짐

## 9. Definition of Done

- `configs/agents/game_concept_generator.yaml` 이 추가된다
- `load_registry()` 테스트가 새 agent를 포함해 통과한다
- 기존 agent 파일 형식과 일관된 스타일을 유지한다
- `README.md` 가 persona 예제 1개만 포함한다
- 새 skill이 생성되고 기본 검증을 통과한다
- 루트 `AGENTS.md` 가 로컬 skill 사용 규칙을 명시한다
- 문서상 새 persona와 skill의 목적, 사용 범위, 제약이 명확하다

## 10. Constraints

- 기존 agent YAML 구조를 변경하지 않는다
- 런타임 코드 변경은 하지 않는다
- 한국어 중심 문체를 유지하되, 사용자 제공 영문 역할명은 의미 손상 없이 반영한다
- 수동 편집은 `apply_patch` 로만 수행한다
- skill은 저장소 내부 규칙으로 관리한다
- 로컬 skill의 사용 조건은 `AGENTS.md` 에 명시한다

## Concerns and Design Choices

### D1. Agent ID 네이밍

옵션 A: `game_concept_generator`  
옵션 B: `concept_generator`  
옵션 C: `game_director`

권장안: 옵션 A

이유:

- 역할이 가장 직접적으로 드러난다.
- 다른 도메인 concept generator와 충돌 가능성이 낮다.
- crew YAML에서 읽을 때 목적이 명확하다.

### D2. 이번 변경 범위

옵션 A: agent persona만 추가  
옵션 B: agent persona와 persona 추가 skill까지 같이 추가

권장안: 옵션 B

이유:

- 사용자가 명시적으로 재사용 가능한 skill 생성을 요청했다.
- crew 추가는 여전히 범위 밖으로 유지할 수 있다.
- 이번에 규칙을 묶어두면 다음 요청의 반복 비용이 줄어든다.

### D3. 프롬프트 언어 구성

옵션 A: 전부 한국어로 정리  
옵션 B: 제공된 영어 제목/역할을 살리고 핵심 지시는 한국어로 정리  
옵션 C: 입력 문구를 거의 그대로 이중언어로 보존

권장안: 옵션 B

이유:

- 기존 프로젝트 문체는 한국어 중심이다.
- 역할명 `Game Concept Generator` 는 외부 식별자처럼 남기는 편이 자연스럽다.
- 완전 이중언어는 agent prompt를 불필요하게 길게 만들 수 있다.

### D4. Skill 저장 위치

옵션 A: `skills/` 아래 저장소 내부 skill로 생성  
옵션 B: `/Users/sean/.codex/skills` 아래 전역 skill로 생성

선택: 옵션 A

이유:

- 사용자가 저장소 내부 규칙을 명시적으로 요구했다.
- 프로젝트와 함께 버전 관리된다.
- 다만 다음 세션에서 확실히 사용되게 하려면 `AGENTS.md` 에 명시 연결이 필요하다.

### D5. 로컬 skill 연결 방식

옵션 A: skill 폴더만 추가  
옵션 B: skill 폴더와 루트 `AGENTS.md` 연결 규칙을 같이 추가

권장안: 옵션 B

이유:

- 저장소 내부 skill은 자동 discovery보다 저장소 규칙 노출이 더 중요하다.
- `AGENTS.md` 가 있어야 다음 세션의 에이전트가 언제 이 skill을 써야 하는지 판단하기 쉽다.
- README는 사용자 문서, `AGENTS.md` 는 에이전트 동작 규칙으로 역할이 다르다.

### D6. README persona 예제 정책

옵션 A: persona 예제를 여러 개 유지  
옵션 B: persona 예제는 1개만 두고 나머지는 구조 설명만 유지

권장안: 옵션 B

이유:

- 사용자의 명시 요청과 일치한다.
- 예제가 많을수록 README가 실제 설정 파일과 어긋날 가능성이 커진다.
- 단일 예제로 패턴만 보여주고, 실체는 `configs/agents/` 를 참조하게 하는 편이 유지보수에 유리하다.

## Ticket Plan

### T1. Persona YAML 추가

상태: Completed (2026-03-07)

- 목적: 기존 형식에 맞는 `game_concept_generator` agent 정의 추가
- 변경 파일:
  - `configs/agents/game_concept_generator.yaml`
- 구현 상세:
  - role/goal/backstory/rules를 기존 agent 스타일에 맞춰 정리
  - 사용자 제공 요구사항을 rules에 명확히 반영
- 완료 기준:
  - 새 persona YAML이 schema에 맞게 로드된다
- 검증:
  - `uv run pytest tests/test_persona_loader.py`

### T2. 레지스트리 테스트 갱신

상태: Completed (2026-03-07)

- 목적: 샘플 config 로딩 테스트가 새 agent를 인지하도록 수정
- 변경 파일:
  - `tests/test_persona_loader.py`
- 구현 상세:
  - expected agent set에 `game_concept_generator` 추가
- 완료 기준:
  - 관련 테스트가 통과한다
- 검증:
  - `uv run pytest tests/test_persona_loader.py`

### T3. README 단일 예제 정책 반영

상태: Completed (2026-03-07)

- 목적: 저장소 문서가 persona 예제 1개만 유지하도록 정리
- 변경 파일:
  - `README.md`
- 구현 상세:
  - persona 예제는 1개만 유지
  - 나머지는 구조 설명 또는 경로 안내로 압축
- 완료 기준:
  - 문서와 실제 config 상태가 어긋나지 않는다
- 검증:
  - 문서 확인

### T4. InhouseCrew persona 추가 skill 생성

상태: Completed (2026-03-07)

- 목적: 이후 같은 작업을 반복 설명 없이 수행할 수 있는 재사용 skill 추가
- 변경 파일:
  - `skills/inhouse-crew-add-agent-persona/SKILL.md`
  - 필요 시 `skills/inhouse-crew-add-agent-persona/references/*.md`
- 구현 상세:
  - 저장소 내부 skill 구조를 만든다
  - InhouseCrew의 `configs/agents`, `tests/test_persona_loader.py`, `README.md` 정책을 반영
  - 다음 요청에서 언제 이 skill을 써야 하는지 frontmatter description에 명시
- 완료 기준:
  - skill 구조가 생성되고 내용 검토 기준을 충족한다
- 검증:
  - `sed -n '1,220p' skills/inhouse-crew-add-agent-persona/SKILL.md`

### T5. 로컬 skill 연결 규칙 추가

상태: Completed (2026-03-07)

- 목적: 다음 세션에서 저장소 규칙만으로도 로컬 skill 사용을 유도
- 변경 파일:
  - `AGENTS.md`
- 구현 상세:
  - 로컬 skill 목록에 `inhouse-crew-add-agent-persona` 추가
  - agent persona 추가/수정 요청 시 이 skill을 먼저 읽도록 트리거 조건 명시
- 완료 기준:
  - 저장소 규칙에서 로컬 skill 경로와 사용 시점이 명확하다
- 검증:
  - `sed -n '1,240p' AGENTS.md`
