# Inhouse Crew Bootstrap Implementation

상태: Completed  
작성일: 2026-03-07  
티켓 구현 및 검증 완료

## 1. Goal and Background

이 프로젝트의 목표는 CrewAI를 원본 수정 없이 상위 레이어에서 확장해, 로컬에 로그인된 Codex 세션을 사용하는 인하우스 Crew 실행 환경을 만드는 것이다.

현재 기준 입력 문서에서 확인된 핵심 요구는 다음과 같다.

- `crewai` 원본, vendor 코드, private API를 수정하지 않는다.
- 확장은 configuration/composition/adapter/workspace 레이어로 분리한다.
- 에이전트 persona는 YAML 데이터로 관리하고 코드와 분리한다.
- 결과물은 task 단위 폴더와 Markdown 산출물 중심으로 남긴다.
- 초기 구현 범위는 `Custom LLM`, `YAML persona`, `task별 결과 저장` 3가지다.

추가로 현재 로컬 환경을 점검한 결과:

- `uv 0.10.7` 설치됨
- `codex-cli 0.108.0-alpha.12` 설치됨
- `node v22.22.0`, `npm 10.9.4` 설치됨
- `python3 3.9.6` 사용 중

이 중 Python 버전은 CrewAI 공식 설치 요구사항(`>=3.10, <3.14`)을 만족하지 않으므로, 실제 구현 전 Python 3.10 이상 환경부터 고정해야 한다.

## 2. Scope

### In Scope

- Python 패키지 구조와 실행 엔트리포인트 초기 셋업
- YAML 기반 agent/crew/settings 로딩 구조
- CrewAI `BaseLLM` 기반 `CodexCliLLM` 어댑터 초안
- task/workspace 산출물 저장 구조
- planning/coding/review 용 기본 crew 조립 구조
- 최소 1개의 샘플 실행 경로와 문서화

### Out of Scope

- CrewAI 원본 수정
- Codex OAuth 내부 토큰 구조 파싱 또는 비공식 인증 재사용
- 복잡한 멀티턴 세션 유지형 Codex 런타임
- UI/웹 프론트엔드
- 고급 observability, queue, remote runner

## 3. User Scenarios

1. 운영자는 persona YAML만 수정해 planner/developer/reviewer의 역할과 규칙을 바꾸고 싶다.
2. 운영자는 로컬에 로그인된 Codex CLI를 CrewAI의 LLM처럼 연결하고 싶다.
3. 운영자는 실행 결과를 `workspace/runs/...` 아래 Markdown 산출물로 남기고 싶다.
4. 운영자는 feature delivery crew를 CLI로 실행하고, 어떤 입력과 산출물이 오갔는지 재현 가능하게 확인하고 싶다.

## 4. Feature List with Priorities

### P0

- Python 3.10+ 기반 프로젝트 스캐폴드와 의존성 고정
- `configs/agents`, `configs/crews`, `configs/settings.yaml` 구조 정의
- persona/settings schema 검증 로더
- `CodexCliLLM` 커스텀 LLM 어댑터
- task workspace 생성 및 Markdown 결과 저장
- `crew_factory.py` 기반 조립 로직

### P1

- planning/coding/review 도메인 crew 모듈화
- CLI 엔트리포인트와 샘플 실행
- 통합 테스트와 실패 시 디버깅 로그 남기기

### P2

- tool registry 확장
- run metadata 강화
- 관측성/추적 시스템 연동

## 5. Data and Model

권장 데이터 모델:

- `AppSettings`
  - `workspace_root`
  - `default_llm`
  - `codex_command`
  - `timeout_seconds`
  - `retry_count`
- `AgentPersona`
  - `id`, `role`, `goal`, `backstory`, `rules`
  - `allow_delegation`, `verbose`, `llm`, `tools`
- `CrewSpec`
  - `id`, `agents`, `process`, `tasks`, `output_policy`
- `TaskRunContext`
  - `run_id`, `task_id`, `crew_id`, `started_at`, `input_summary`
- `TaskArtifact`
  - `artifact_type`, `path`, `content_type`, `created_at`

권장 폴더 구조:

```text
InhouseCrew/
├─ pyproject.toml
├─ .env.example
├─ configs/
│  ├─ agents/
│  ├─ crews/
│  └─ settings.yaml
├─ src/
│  └─ inhouse_crew/
│     ├─ __init__.py
│     ├─ main.py
│     ├─ crew_factory.py
│     ├─ persona_loader.py
│     ├─ settings_loader.py
│     ├─ task_workspace.py
│     ├─ llms/
│     │  ├─ codex_cli_llm.py
│     │  └─ codex_runner.py
│     ├─ tools/
│     │  ├─ file_ops.py
│     │  └─ official_tools.py
│     └─ domain/
│        ├─ planning_crew.py
│        ├─ coding_crew.py
│        └─ review_crew.py
├─ tests/
└─ workspace/
   └─ runs/
```

## 6. API / Events / Flow

### Bootstrap Flow

1. CLI 진입점이 crew ID와 입력 경로를 받는다.
2. `settings_loader`가 환경 변수와 `configs/settings.yaml`을 읽는다.
3. `persona_loader`가 agent/crew YAML을 로딩하고 schema를 검증한다.
4. `crew_factory`가 persona, LLM, tools, task 정책을 조합해 Crew 인스턴스를 만든다.
5. `task_workspace`가 run/task 디렉터리를 만들고 입력 메타데이터를 저장한다.
6. Crew 실행 후 결과를 Markdown 아티팩트로 저장한다.

### LLM Adapter Flow

1. CrewAI가 `CodexCliLLM.call(...)`을 호출한다.
2. 어댑터는 prompt/messages를 Codex CLI 입력 형식으로 정규화한다.
3. `codex_runner`가 로컬 Codex CLI를 단발성 subprocess로 실행한다.
4. stdout/stderr/exit code를 수집하고 timeout/retry 정책을 적용한다.
5. 성공 시 text 응답을 CrewAI에 반환하고, 실패 시 명시적 예외로 래핑한다.

MVP에서는 function calling 또는 tool call passthrough를 직접 구현하지 않고, `supports_function_calling()`은 `False`로 시작하는 것이 안전하다. 파일 수정이나 shell 실행 책임은 LLM이 아니라 별도 tool/workflow에 둔다.

## 7. UI / UX

UI 범위는 없고, 초기 인터페이스는 CLI와 Markdown 산출물이다.

필수 사용자 경험:

- 실행 커맨드가 단순해야 한다.
- 실패 이유가 stdout/stderr/timeout 기준으로 분리되어 보여야 한다.
- 산출물 경로가 일관되어야 한다.
- YAML 수정 후 재실행이 쉬워야 한다.

## 8. Error and Edge Cases

- Python 버전이 3.10 미만인 경우 설치 자체를 차단
- `codex` 명령이 없거나 로그인되지 않은 경우 초기 진단 실패
- Codex CLI 출력 형식이 변경된 경우 파서 실패
- YAML 필수 필드 누락 또는 tool/llm 참조 불일치
- CrewAI 업데이트로 `BaseLLM` 요구 인터페이스가 변경되는 경우
- task 결과가 비어 있거나 Markdown 저장 중 I/O 오류가 나는 경우
- 장시간 실행으로 timeout이 발생하는 경우

## 9. Definition of Done

- Python 3.10+ 환경에서 `uv sync` 또는 동등한 설치 절차가 성공한다.
- persona/crew/settings YAML 샘플이 로드되고 schema 검증을 통과한다.
- `CodexCliLLM`이 CrewAI `BaseLLM` 규약을 만족한다.
- 샘플 crew가 로컬 Codex CLI를 통해 한 번 이상 성공 실행된다.
- 실행 결과가 `workspace/runs/.../*.md`에 저장된다.
- 핵심 모듈 단위 테스트와 최소 통합 테스트가 통과한다.
- README 또는 별도 운영 문서에 실행 방법이 기록된다.

## 10. Constraints

- `crewai` 원본 수정 금지
- monkey patch / private API 의존 금지
- 공식 문서 기준 확장 포인트 우선 사용
- persona는 YAML 데이터로 유지
- 산출물은 Markdown 우선
- LLM은 응답 생성 책임만 갖고 파일 저장 정책은 갖지 않음
- 설정과 실행 책임을 분리

## Design Decisions to Confirm Before Coding

### D1. 설정 파일 위치

옵션 A: `configs/`를 루트에 둔다.  
옵션 B: CrewAI 기본 스캐폴드처럼 `src/inhouse_crew/config/` 아래 둔다.

권장안: 옵션 A.

이유:

- 입력 문서의 권장 구조와 일치한다.
- 설정 데이터와 코드가 더 명확히 분리된다.
- `CrewBase` 기본 스캐폴드와 조금 다르지만, 이번 구조는 자체 loader/factory를 쓰므로 제약이 작다.

### D2. Codex 연동 방식

옵션 A: `codex` CLI를 subprocess로 단발 호출한다.  
옵션 B: OpenAI API 키 방식으로 우회한다.

권장안: 옵션 A.

이유:

- 요구사항이 "로컬 OAuth Codex 세션" 활용에 맞춰져 있다.
- 비공식 토큰 재사용이나 인증 구조 의존을 피할 수 있다.
- 다만 CLI 출력 형식 안정성은 검증이 필요하다.

### D3. 첫 구현 범위에서 tool calling 지원 여부

옵션 A: MVP에서는 미지원으로 두고 텍스트 completion만 안정화한다.  
옵션 B: 처음부터 tool call passthrough까지 구현한다.

권장안: 옵션 A.

이유:

- CrewAI `BaseLLM` 최소 계약으로 먼저 정상 동작 경로를 확보하는 편이 리스크가 낮다.
- 입력 문서도 파일 수정/셸 실행 책임을 별도 tool/workflow로 분리하라고 명시한다.

## Ticket Plan

### T1. Environment and Project Bootstrap

Status: Completed (2026-03-07)

Verification:

- `uv sync`
- `uv run python --version` -> `Python 3.12.12`
- `uv run python -c "import crewai; print(crewai.__version__)"` -> `1.10.1`

목적:

- Python 3.10+ 기준으로 프로젝트 초기 골격과 패키징을 확정한다.

Changed files:

- `pyproject.toml`
- `.gitignore`
- `.env.example`
- `src/inhouse_crew/__init__.py`
- `README.md`

Implementation details:

- `uv` 기반 패키지 초기화
- CrewAI 및 YAML/schema/test 의존성 추가
- Python 버전 제약 명시
- 기본 엔트리포인트와 개발용 명령 정리

Acceptance criteria:

- 의존성 설치가 재현 가능하다.
- Python 버전 제약이 문서와 설정에 반영된다.

### T2. Config Schema and Sample YAML

Status: Completed (2026-03-07)

Verification:

- `uv run pytest tests/test_persona_loader.py tests/test_settings_loader.py`
- `uv run ruff check src tests`

목적:

- persona/crew/settings를 데이터로 관리할 수 있게 한다.

Changed files:

- `configs/agents/*.yaml`
- `configs/crews/*.yaml`
- `configs/settings.yaml`
- `src/inhouse_crew/persona_loader.py`
- `src/inhouse_crew/settings_loader.py`

Implementation details:

- Pydantic 또는 동등한 schema 계층 도입
- YAML 필수 필드와 기본값 검증
- 샘플 planner/developer/reviewer persona 추가

Acceptance criteria:

- 잘못된 YAML에서 명시적 검증 오류가 난다.
- 유효한 YAML에서 파이썬 객체 변환이 가능하다.

### T3. Codex Runner and Custom LLM Adapter

Status: Completed (2026-03-07)

Verification:

- `uv run pytest tests/llms/test_codex_cli_llm.py`
- `uv run ruff check src tests`
- `uv run python - <<'PY' ... CodexCliLLM().call("Reply with exactly PONG") ... PY` -> `PONG`

목적:

- CrewAI에서 사용할 `CodexCliLLM` 최소 동작 버전을 만든다.

Changed files:

- `src/inhouse_crew/llms/codex_runner.py`
- `src/inhouse_crew/llms/codex_cli_llm.py`
- `tests/llms/test_codex_cli_llm.py`

Implementation details:

- CrewAI `BaseLLM` 계약에 맞춘 클래스 구현
- subprocess 호출, timeout, retry, stderr 처리
- MVP에서는 텍스트 응답 중심으로만 지원

Acceptance criteria:

- mock 기반 단위 테스트 통과
- 최소 프롬프트 호출이 string 응답을 반환한다.

### T4. Workspace Artifact Management

Status: Completed (2026-03-07)

Verification:

- `uv run pytest tests/test_task_workspace.py`
- `uv run ruff check src tests`

목적:

- 실행 단위별 입력/출력/메타데이터를 Markdown 중심으로 저장한다.

Changed files:

- `src/inhouse_crew/task_workspace.py`
- `tests/test_task_workspace.py`

Implementation details:

- `workspace/runs/<run_id>/<task_id>/` 생성
- `input.md`, `result.md`, `metadata.json` 또는 동등 파일 저장
- 경로 정책 일원화

Acceptance criteria:

- 실행 결과 파일이 예측 가능한 위치에 생성된다.
- 저장 실패 시 예외가 명확하다.

### T5. Crew Factory and Domain Crews

Status: Completed (2026-03-07)

Verification:

- `uv run pytest tests/test_crew_factory.py`
- `uv run ruff check src tests`
- `uv run python - <<'PY' ... CrewFactory.from_paths(...).create_crew('feature_delivery') ... PY` -> `3 3 plan_feature`

목적:

- persona, LLM, tools, task 정책을 조합해 실행 가능한 crew를 만든다.

Changed files:

- `src/inhouse_crew/crew_factory.py`
- `src/inhouse_crew/domain/planning_crew.py`
- `src/inhouse_crew/domain/coding_crew.py`
- `src/inhouse_crew/domain/review_crew.py`

Implementation details:

- crew spec 기반 factory 구현
- 역할별 기본 crew 조합
- tool registry와 LLM registry 연결

Acceptance criteria:

- 샘플 crew 생성이 가능하다.
- 잘못된 agent/tool 참조에서 조립 단계 오류가 난다.

### T6. CLI Entry and End-to-End Smoke Path

Status: Completed (2026-03-07)

Verification:

- `uv run pytest tests/test_main.py tests/test_task_workspace.py tests/test_persona_loader.py`
- `uv run ruff check src tests`
- `uv run inhouse-crew run --crew-id quickstart --input "..."` -> `workspace/runs/.../summary.md`

목적:

- 사용자가 실제로 실행 가능한 최소 경로를 만든다.

Changed files:

- `src/inhouse_crew/main.py`
- `README.md`
- 필요 시 `tests/e2e/test_smoke.py`

Implementation details:

- CLI 인자 파싱
- 설정 로딩, workspace 생성, crew 실행 연결
- 샘플 사용법 문서화

Acceptance criteria:

- 단일 명령으로 샘플 실행이 가능하다.
- 결과 Markdown 경로를 출력한다.

### T7. Verification and Hardening

Status: Completed (2026-03-07)

Verification:

- `uv run pytest` -> `15 passed`
- `uv run ruff check src tests` -> `All checks passed`
- `uv build` -> `dist/inhouse_crew-0.1.0.tar.gz`, `dist/inhouse_crew-0.1.0-py3-none-any.whl`
- `uv run inhouse-crew run --crew-id quickstart --input "Summarize the current bootstrap status in two bullets."`

목적:

- 기본 품질 게이트와 운영 문서를 정리한다.

Changed files:

- `tests/**`
- `README.md`
- `docs/**`

Implementation details:

- lint/typecheck/test 명령 정리
- 실패 케이스 보강
- 남은 제약과 알려진 리스크 문서화

Acceptance criteria:

- 핵심 검증 명령이 통과한다.
- 잔여 리스크가 문서에 남는다.

## Recommended Execution Order

T1 → T2 → T3 → T4 → T5 → T6 → T7

이 순서가 맞는 이유는, Python/의존성 기준과 설정 schema가 먼저 고정되어야 LLM adapter와 crew 조립이 흔들리지 않기 때문이다.

## Risks and Open Questions

- 현재 시스템 Python 3.9.6이므로 가상환경 기준 Python 3.10+ 확보가 선행되어야 한다.
- Codex CLI를 단발 호출할 때 어떤 비대화형 명령 패턴이 가장 안정적인지 실제 검증이 필요하다.
- CrewAI 버전별 `BaseLLM` 세부 인터페이스 차이가 있을 수 있어 구현 시점에 정확한 버전 핀 고정이 필요하다.

## Residual Risks

- Codex CLI 실행 시 stderr로 MCP startup 경고와 외부 MCP 인증 실패 로그가 섞여 나올 수 있다. 현재 어댑터는 종료 코드와 최종 응답 파일을 기준으로 성공 여부를 판단한다.
- native function calling은 의도적으로 비활성화되어 있다. tool passthrough가 필요한 시나리오는 다음 단계에서 별도 설계가 필요하다.
- quickstart 스모크는 통과했지만, `feature_delivery` 같은 다중 task crew는 프롬프트 크기와 응답 시간에 따라 실행 시간이 더 길 수 있다.

## References

- Guide 입력 문서: `Guide.md`
- 구조 제안 입력 문서: `Recommand.md`
- CrewAI 공식 설치 문서: https://docs.crewai.com/en/installation
- CrewAI 공식 Custom LLM 문서: https://docs.crewai.com/en/learn/custom-llm
- CrewAI 공식 Agents 개념 문서: https://docs.crewai.com/en/concepts/agents
- OpenAI 공식 Codex 문서: https://developers.openai.com/codex/cli
