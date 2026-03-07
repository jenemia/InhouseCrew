# Codex 실행 실패 처리 구현 명세

## 상태

- 단계: 완료
- 전체 상태: T1-T3 완료
- 권장안: 로컬 Codex 시작 문제를 조기에 실패 처리하고, 구조화된 실패 산출물을 워크스페이스에 남긴다

## 1. 목표와 배경

현재 `inhouse-crew run` 경로는 Codex 서브프로세스 실패를 CrewAI를 통해 그대로 노출하지만, 실제 운영자 관점에서는 출력이 시끄럽고 진단 정보가 충분히 남지 않는다.

확인한 사실:
- 현재 환경에서 일반 `quickstart` 실행은 정상 성공한다.
- 강제로 Codex 시작 실패를 만들면 (`INHOUSE_CREW_CODEX_COMMAND=definitely-missing-command`) 사용자가 본 것과 같은 경고 계열이 재현된다.
  - `task_failed` / `crew_kickoff_failed` 이벤트 짝 불일치
  - 트레이스백 시작 지점은 [`src/inhouse_crew/llms/codex_runner.py`](/Users/sean/Documents/InhouseCrew/src/inhouse_crew/llms/codex_runner.py):56 이다.
- 재현된 실패의 실제 원인은 `subprocess.run(...)` 호출 중 발생한 `FileNotFoundError`가 `CodexExecutionError`로 변환되어 올라오는 것이다.
- 실패한 실행은 현재 최종 상태나 구조화된 에러 산출물을 남기지 못한 채 워크스페이스 디렉터리만 부분적으로 생성한다.

추론:
- 사용자가 본 경고는 2차 증상일 가능성이 높다.
- 1차 원인은 Codex CLI 시작 또는 실행 실패이고, 현재 프로젝트 레이어가 그 실패를 워크스페이스에 충분히 보존하지 못하고 있다.

## 2. 범위

포함:
- Codex CLI 실행 주변의 프로젝트 소유 실패 처리 개선
- 워크스페이스에 진단 가능한 실패 정보 저장
- 흔한 로컬 설정 오류를 더 이른 시점에 더 명확히 실패 처리
- 새 동작에 대한 회귀 테스트 추가

제외:
- `.venv/` 아래 CrewAI 벤더 코드 수정
- 에이전트/태스크 프롬프트 설계 변경
- 외부 트레이싱 또는 관측 시스템 추가

## 3. 사용자 시나리오

1. 개발자가 `uv run inhouse-crew run ...` 을 실행했는데 로컬 `codex` 바이너리가 없다.
2. 개발자가 crew를 실행했는데 `codex exec` 가 인증, 설정, CLI 시작 문제로 non-zero 종료한다.
3. 실행 도중 실패했을 때 운영자가 터미널 스크롤백 없이도 실패한 명령, stderr, 최종 상태를 워크스페이스에서 바로 확인해야 한다.
4. 성공 실행의 기존 동작은 그대로 유지되어야 한다.

## 4. 기능 목록과 우선순위

P0:
- `codex` 실행 파일 누락을 반복 재시도 전에 감지한다.
- 실패한 run/task 상태를 워크스페이스 메타데이터에 기록한다.
- 사람이 읽을 수 있는 실패 요약과 기계가 읽을 수 있는 상세 진단 정보를 남긴다.

P1:
- 가능할 때 실행된 명령, 반환 코드, stderr/stdout 일부를 실패 산출물에 포함한다.
- 최종 예외 메시지는 운영자 관점에서 간결하게 유지한다.

P2:
- 필요하면 알려진 로컬 문제에 대한 환경 진단을 후속으로 추가 검토한다.

## 5. 데이터와 모델

추가할 프로젝트 소유 데이터:
- Run 메타데이터
  - `status: "failed"`
  - `failed_at`
  - `error_type`
  - `error_message`
- 실패한 Task 메타데이터
  - `status: "failed"`
  - `failed_at`
  - `error_type`
  - `error_message`
- Run 또는 Task 디렉터리에 실패 산출물 파일
  - 사람이 읽는 Markdown 요약
  - 자동 처리용 JSON 상세 정보

가능한 JSON 필드:
- `error_type`
- `error_message`
- `command`
- `returncode`
- `stdout`
- `stderr`

## 6. API / 이벤트 / 흐름

현재 실패 흐름:
1. `CodexRunner._run_once()` 가 `subprocess.run(...)` 을 호출한다.
2. 로컬 시작/실행 오류가 `CodexExecutionError` 로 변환되어 올라온다.
3. CrewAI가 내부 재시도를 하면서 이벤트 버스 경고를 출력하고 최종적으로 kickoff를 중단한다.
4. `run_crew()` 는 최종 워크스페이스 상태를 쓰기 전에 예외로 종료한다.

제안 흐름:
1. crew kickoff 전 또는 첫 runner 사용 시점에 로컬 `codex` 실행 가능 여부를 검증한다.
2. `CodexRunner` 실패 시 구조화된 진단 정보를 보존하는 프로젝트 예외를 올린다.
3. 프로젝트/CLI 레이어에서 run 단위 예외를 잡는다.
4. 실패한 task/run 메타데이터와 산출물을 기록한다.
5. 터미널 사용자에게는 간결한 실패 메시지를 다시 올린다.

## 7. UI / UX

터미널 UX 목표:
- 마지막 부분에 근본 원인이 한 줄로 명확하게 보인다.
- 워크스페이스 경로는 유지되고, 읽기 쉬운 실패 요약 문서가 남는다.
- 진단을 위해 CrewAI 이벤트 경고에 의존하지 않게 한다.

워크스페이스 UX 목표:
- 실패한 run 은 `run-metadata.json` 만 봐도 즉시 드러난다.
- 운영자가 실패 원인을 확인하려고 터미널 스크롤백으로 돌아가지 않아도 된다.

## 8. 오류와 엣지 케이스

- `PATH` 에 `codex` 바이너리가 없음
- `codex exec` 가 `last-message.txt` 를 쓰지 못하고 non-zero 종료
- `codex exec` 타임아웃
- `codex exec` 가 0으로 종료했지만 최종 응답이 없음
- 워크스페이스 실패 산출물 기록 자체가 실패함
- 기존 성공 경로가 깨지면 안 됨

## 9. 완료 조건

- `codex` 명령 누락 시 프로젝트 소유의 직접적인 오류 메시지가 나온다.
- 실패한 run 은 미완성 디렉터리로 끝나지 않고 명시적으로 `failed` 상태가 기록된다.
- 터미널 스크롤백 없이도 Codex 실패 원인을 진단할 수 있을 만큼의 정보가 워크스페이스에 남는다.
- 기존 성공 quickstart 흐름은 그대로 동작한다.
- 최소한 missing-command 와 non-zero-exit 케이스에 대한 자동 테스트가 있다.

## 10. 제약 조건

- `.venv/` 아래 CrewAI 벤더 파일은 수정하지 않는다.
- 주석은 현재 저장소 스타일처럼 짧고 실용적으로 유지한다.
- 구현은 `src/inhouse_crew/**`, 테스트는 `tests/**` 아래에서만 한다.
- 수동 수정은 `apply_patch` 를 사용한다.
- 광범위한 구조 변경보다 실패 처리 보강에 집중한다.

## 설계 논의

### 우려와 위험

- 사용자가 본 원본 트레이스백 전체는 아직 없어서, 정확한 Codex CLI 오류 내용은 동일 실패 계열 재현을 근거로 추론한 상태다.
- CrewAI 이벤트 짝 불일치 경고는 업스트림 동작이다. 더 이르게 실패시키면 일부 줄일 수는 있지만, 벤더 패치 없이 완전히 통제할 수는 없다.
- 실패 산출물에 `stdout` / `stderr` 전체를 담으면 너무 장황해질 수 있으므로 길이 제한이나 선별 저장이 필요할 수 있다.

### 선택이 필요한 설계 결정

1. `codex` 누락을 어디서 조기 실패시킬지
   - 옵션 A: `CodexRunner` 내부에서 `subprocess.run` 전에 검증
   - 옵션 B: `run_from_args` / `run_crew` 에서 crew kickoff 전에 검증
2. 실패 상세 정보를 어디까지 저장할지
   - 옵션 A: 메타데이터만 저장
   - 옵션 B: 메타데이터와 별도 Markdown/JSON 산출물까지 저장
3. CrewAI 경고 자체를 직접 다룰지
   - 옵션 A: 벤더 패치 없이 잔여 경고는 수용
   - 옵션 B: CrewAI 동작을 patch/monkeypatch

### 옵션별 트레이드오프

선택 1:
- 옵션 A는 실제 의존성이 있는 위치에 검증을 두므로, 앞으로 `CodexRunner` 를 다른 경로에서 호출해도 보호된다.
- 옵션 B는 CLI 사용자에게는 조금 더 빨리 실패하지만, 비CLI 호출자를 보호하지 못한다.

선택 2:
- 옵션 A는 단순하지만 운영자가 결국 터미널 스크롤백으로 돌아가야 한다.
- 옵션 B는 코드와 파일 출력이 조금 늘지만, 진단 가능성을 크게 높인다.

선택 3:
- 옵션 A는 책임 경계를 깔끔하게 유지하고 업그레이드 리스크가 낮다.
- 옵션 B는 경고를 더 숨길 수는 있지만, CrewAI 내부 구현에 결합되어 버전 업 시 깨지기 쉽다.

### 권장안과 근거

권장:
- 선택 1: 옵션 A
- 선택 2: 옵션 B
- 선택 3: 옵션 A

근거:
- Codex 의존성 검증과 워크스페이스 진단 정보는 이 프로젝트가 직접 책임지는 편이 맞다.
- 경고를 숨기기 위해 CrewAI monkeypatch 를 추가하는 것은 유지보수 비용이 크다.
- 위 조합이 가장 작은 범위의 수정으로 실제 실패 경로를 개선하고, 테스트 가능성과 업그레이드 안정성도 유지한다.

### 티켓 실행 순서

1. T1: Codex 의존성 검증과 구조화된 runner 진단 추가
2. T2: 실패한 run/task 상태와 산출물 워크스페이스 기록
3. T3: 회귀 테스트와 검증

## 티켓

### T1. Codex 의존성 검증과 Runner 진단 정보 구조화

- 상태: 완료
- 목적: 로컬 Codex 실행 파일 또는 서브프로세스 호출이 잘못된 경우 명확히 실패시키고, 구조화된 진단 정보를 보존한다.
- 변경 파일:
  - `src/inhouse_crew/llms/codex_runner.py`
  - 새 타입을 export 해야 하면 `src/inhouse_crew/llms/__init__.py`
- 구현 내용:
  - 설정된 명령에 대한 명시적 preflight 체크를 추가한다.
  - missing-command, timeout, non-zero-exit, empty-response 케이스의 상세 정보를 구조화해 보존한다.
  - 성공 경로 동작은 바꾸지 않는다.
- 완료 기준:
  - missing-command 실패가 프로젝트 소유 메시지로 명확히 드러난다.
  - non-zero 종료 시 유용한 진단 필드가 남는다.
- 검증 방법:
  - missing-command, non-zero-exit 단위 테스트
- 검증 결과:
  - `uv run pytest tests/llms/test_codex_cli_llm.py` 통과

### T2. 실패한 Run / Task 산출물 기록

- 상태: 완료
- 목적: 실패한 run 을 터미널 출력이 아니라 워크스페이스 산출물만으로도 진단 가능하게 만든다.
- 변경 파일:
  - `src/inhouse_crew/main.py`
  - `src/inhouse_crew/task_workspace.py`
  - 필요하면 `src/inhouse_crew/` 아래 작은 helper 모듈 추가
- 구현 내용:
  - 워크스페이스 생성 이후의 run 단위 예외를 잡는다.
  - 실패한 task 와 run 을 `failed` 상태로 기록한다.
  - 사람이 읽는 문서와 구조화된 상세 정보를 함께 쓴다.
  - 기록 후에는 간결한 예외를 다시 올린다.
- 완료 기준:
  - 실패한 run 에 `status: failed` 메타데이터가 기록된다.
  - 워크스페이스에 읽을 수 있는 실패 산출물이 생긴다.
- 검증 방법:
  - `run_crew()` 또는 CLI 경로 기준의 통합 성격 테스트
- 검증 결과:
  - `INHOUSE_CREW_CODEX_COMMAND=definitely-missing-command uv run inhouse-crew run --crew-id quickstart --input 'failure repro after t2'` 수동 재현으로 `run-metadata.json`, `summary.md`, `failure.json`, task `result.md`, task `failure.json` 기록 확인

### T3. 회귀 테스트와 최종 검증

- 상태: 완료
- 목적: 실패 보고 동작의 회귀를 막고 성공 경로를 보호한다.
- 변경 파일:
  - `tests/llms/test_codex_cli_llm.py`
  - 필요하면 `tests/` 아래 새 테스트 파일
- 구현 내용:
  - 구조화된 진단 정보와 실패 워크스페이스 기록에 대한 집중 테스트를 추가한다.
  - 관련 테스트와 quickstart 스모크를 다시 실행한다.
- 완료 기준:
  - 새 테스트가 구현 전에는 실패하고 구현 후에는 통과한다.
  - 기존 성공 경로 테스트도 계속 통과한다.
- 검증 방법:
  - `uv run pytest`
  - 대상 `quickstart` 실행 스모크
- 검증 결과:
  - `uv run pytest` 통과
  - `uv run ruff check src tests` 통과
  - `uv run inhouse-crew run --crew-id quickstart --input '실행 성공 스모크를 검증해줘'` 성공
