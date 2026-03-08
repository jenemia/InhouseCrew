# CrewAI Knowledge and Memory Implementation

상태: 구현 완료  
작성일: 2026-03-08

## 1. Goal and Background

이번 변경의 목표는 로컬 Codex를 생성 LLM으로 유지한 채, CrewAI 공식 `Knowledge` 와
`Memory` 기능을 opt-in 방식으로 붙일 수 있게 공통 구조를 추가하는 것이다.

핵심 요구:

- 로컬 Codex는 계속 답변 생성 LLM로 사용
- 임베딩은 Ollama 기반 공식 embedder 사용
- crew별로 `knowledge` 와 `memory` 를 선택적으로 켤 수 있는 config 구조
- `game_design_team` 이 첫 적용 대상
- 다른 crew도 같은 규칙으로 쉽게 확장 가능해야 함

## 2. Scope

### In Scope

- settings schema에 embedder/storage 설정 추가
- crew schema에 optional `knowledge_files`, `memory` 추가
- `CrewFactory` 에 공식 Knowledge/Memory 조립 로직 추가
- `game_design_team` crew에 knowledge/memory 적용
- knowledge 템플릿 파일 추가
- 관련 테스트, README, skill 문서 갱신
- Ollama Python dependency 추가

### Out of Scope

- `run_crew()`의 `user_request` 병합 로직 변경
- 모든 crew에 memory 기본 활성화
- knowledge source를 다중 포맷으로 확장

## 3. User Scenarios

1. 운영자는 고정 게임 컨셉/개발 방향을 knowledge 파일에 두고, 매 요청은 짧게 유지하고 싶다.
2. 운영자는 특정 crew만 memory를 켜서 실행 간 누적 맥락을 유지하고 싶다.
3. 운영자는 다른 crew를 만들 때도 같은 config 규칙으로 knowledge/memory를 opt-in 하고 싶다.

## 4. Feature List with Priorities

### P0

- crew-level optional knowledge/memory schema 추가
- project-local storage 경로 고정
- `game_design_team` knowledge/memory 적용
- 관련 테스트 갱신

### P1

- README와 로컬 skill 규칙 갱신
- `.env.example` 에 storage root 추가

## 5. Data and Model

추가되는 settings 필드:

- `embedder`
- `crewai_storage_root`

추가되는 crew 필드:

- `knowledge_files: list[str]`
- `memory: bool`

project-local 경로 규칙:

- knowledge storage: `workspace/crewai_storage/knowledge`
- memory storage: `workspace/crewai_storage/memory/<crew_id>`
- knowledge 문서 관례: `knowledge/<crew_id>/project_brief.md`

## 6. API / Events / Flow

1. settings loader가 embedder/storage 설정을 읽는다.
2. crew spec loader가 optional `knowledge_files`, `memory` 를 읽는다.
3. `CrewFactory.create_crew()` 는 필요 시 embedder를 초기화한다.
4. knowledge 파일이 있으면 경로를 검증하고 `TextFileKnowledgeSource` 기반 knowledge를 만든다.
5. memory가 켜져 있으면 crew별 local path의 `Memory` 인스턴스를 만든다.
6. 생성 LLM은 기존처럼 `CodexCliLLM` 을 사용한다.

## 7. UI / UX

UI 변경은 없다. 사용자는 긴 고정 프롬프트 대신 knowledge 파일을 수정하는 방식으로
기본 컨텍스트를 유지할 수 있다.

## 8. Error and Edge Cases

- embedder 설정이 없는데 knowledge/memory가 켜져 있으면 fail-fast
- knowledge 파일 경로가 없으면 fail-fast
- Ollama python dependency가 없으면 embedder 생성 시 fail-fast
- Ollama 서버 미실행 등으로 knowledge 초기화가 실패하면 factory 단계에서 명시적으로 surface
- memory는 project-local 저장소를 사용해야 하므로 appdir 기본값에 의존하지 않음

## 9. Definition of Done

- settings 와 crew schema가 knowledge/memory opt-in 을 지원한다
- `game_design_team` 이 knowledge/memory 설정을 가진다
- 관련 테스트가 통과한다
- README 와 로컬 skill 문서가 새 표준을 반영한다
- smoke 수준에서 knowledge/memory 경로 조립이 확인된다

## 10. Constraints

- 로컬 Codex를 생성 LLM에서 제거하지 않는다
- `src/inhouse_crew/domain/` wrapper는 추가하지 않는다
- 수동 편집은 `apply_patch` 로만 수행한다
- README persona 예제는 1개만 유지한다

## Ticket Plan

### T1. Settings / Crew Schema 확장

상태: Done

- 변경 파일:
  - `src/inhouse_crew/settings_loader.py`
  - `src/inhouse_crew/persona_loader.py`
  - `configs/settings.yaml`
  - `.env.example`
- 검증:
  - `uv run pytest tests/test_settings_loader.py tests/test_persona_loader.py`

### T2. CrewFactory Knowledge/Memory 조립

상태: Done

- 변경 파일:
  - `src/inhouse_crew/crew_factory.py`
  - `tests/test_crew_factory.py`
- 검증:
  - `uv run pytest tests/test_crew_factory.py`

### T3. game_design_team 적용

상태: Done

- 변경 파일:
  - `configs/crews/game_design_team.yaml`
  - `knowledge/game_design_team/project_brief.md`
  - `tests/test_persona_loader.py`
- 검증:
  - `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py`

### T4. Repo 규칙 및 문서 갱신

상태: Done

- 변경 파일:
  - `README.md`
  - `AGENTS.md`
  - `skills/inhouse-crew-add-game-design-pipeline/SKILL.md`
- 검증:
  - 문서 확인

### T5. 의존성 및 최종 검증

상태: Done

- 변경 파일:
  - `pyproject.toml`
  - `uv.lock`
- 검증:
  - `uv run pytest tests/test_settings_loader.py tests/test_persona_loader.py tests/test_crew_factory.py`
  - `uv run ruff check src tests`

## Verification Notes

- `uv run pytest tests/test_settings_loader.py tests/test_persona_loader.py tests/test_crew_factory.py` 통과
- `uv run ruff check src tests` 통과
- `uv run python - <<... factory.create_crew("game_design_team") ...` 실행 시 fail-fast 동작 확인
- 현재 로컬 Ollama 서버에는 모델이 비어 있었고, `ollama list` 결과도 empty 상태였다
- 당시 실제 `game_design_team` 초기화는 `model "nomic-embed-text" not found` 오류로 중단됐고, 이는 의도한 사전 검증 동작이었다

## Result Summary

- 로컬 Codex는 계속 생성 LLM로 유지된다
- CrewAI 공식 `Knowledge` 와 `Memory` 를 crew 단위 opt-in 설정으로 일반화했다
- `game_design_team` 은 첫 적용 대상으로 `knowledge/game_design_team/project_brief.md` 를 사용했고,
  이후 운영상 memory를 비활성화했다
- 다른 crew도 같은 schema와 디렉터리 규칙으로 그대로 확장 가능하다

## Follow-up Change Request

작성일: 2026-03-08
상태: 구현 완료

### Goal

- knowledge/memory 기본 Ollama 임베딩 모델을 `nomic-embed-text` 에서
  `qwen3-embedding:4b` 로 변경한다.

### Scope

In:

- settings 기본값 변경
- example env 변경
- README 안내 문구 변경
- settings loader 테스트 기대값 변경
- 실제 crew 초기화 스모크 재확인

Out:

- crew schema 변경
- memory/knowledge 동작 방식 변경
- 사용자별 커스텀 embedder override 제거

### Risks and Notes

- 로컬 Ollama 서버에 `qwen3-embedding:4b` 가 실제로 pull 되어 있어야 한다.
- env override 테스트는 그대로 유지하고, 기본값 검증만 새 모델명으로 바꾼다.
- fail-fast 규칙은 유지한다.

### Ticket

#### T6. Default Embedder Model Swap

상태: Done

- 변경 파일:
  - `src/inhouse_crew/settings_loader.py`
  - `configs/settings.yaml`
  - `.env.example`
  - `README.md`
  - `tests/test_settings_loader.py`
- 구현:
  - 기본 embedder model_name 을 `qwen3-embedding:4b` 로 변경
  - README 의 Ollama 준비 절차와 예시 pull 명령도 같은 모델명으로 변경
  - 기본값 검증 테스트를 새 모델명에 맞게 갱신
- 검증:
  - `uv run pytest tests/test_settings_loader.py`
  - `uv run ruff check src tests`
  - `uv run python - <<... factory.create_crew(\"game_design_team\") ...`

### T6 Verification Result

- 기본 embedder model_name 을 `qwen3-embedding:4b` 로 교체했다
- settings/README/example env/test 기대값을 모두 새 모델명으로 동기화했다
- `uv run pytest tests/test_settings_loader.py` 통과
- `uv run ruff check src tests` 통과
- 실제 `factory.create_crew("game_design_team")` 스모크 검증 통과

## Follow-up Change Request

작성일: 2026-03-08
상태: 구현 완료

### Goal

- `game_design_team` 의 memory를 비활성화해 CrewAI memory save analysis 경고를 제거한다.

### Scope

In:

- `game_design_team` crew의 `memory: false` 전환
- loader / factory 테스트 기대값 갱신
- README와 구현 문서에 현재 운영 상태 반영

Out:

- 공통 memory 지원 코드 제거
- 다른 crew의 memory 정책 변경
- embedder 설정 변경

### Risks and Notes

- knowledge는 계속 유지되므로 embedder와 Ollama 준비는 여전히 필요하다.
- 현재 이미 실행 중인 worker나 run에는 소급 적용되지 않는다.
- memory save analysis 경고는 새 실행부터 사라진다.

### Ticket

#### T7. Disable Memory for `game_design_team`

상태: Done

- 변경 파일:
  - `configs/crews/game_design_team.yaml`
  - `tests/test_persona_loader.py`
  - `tests/test_crew_factory.py`
  - `README.md`
  - `docs/crewai-knowledge-memory-implementation.md`
- 구현:
  - `game_design_team`을 knowledge-only 운영으로 전환
  - tests에서 `memory is False` 와 memory builder 미호출 기대값으로 갱신
  - README와 구현 문서 설명을 현재 운영 상태에 맞게 정리
- 검증:
  - `uv run pytest tests/test_persona_loader.py tests/test_crew_factory.py`
  - `uv run ruff check src tests`
