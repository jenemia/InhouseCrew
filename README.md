# InhouseCrew

CrewAI를 원본 수정 없이 상위 레이어에서 확장해, 로컬 Codex CLI 세션을 사용하는 인하우스 Crew 실행 환경을 구축하는 프로젝트다.

## Requirements

- Python `>=3.10,<3.14`
- `uv`
- `codex-cli` (https://developers.openai.com/codex/cli/)

이 저장소는 `uv`가 관리하는 Python 3.12 환경을 기본 기준으로 사용한다.

## Setup

```bash
uv sync
cp .env.example .env
```

가상환경 Python 확인:

```bash
uv run python --version
```

## Run

가장 빠른 스모크 실행:

```bash
uv run inhouse-crew run \
  --crew-id quickstart \
  --input "로컬 Codex 세션을 사용하는 CrewAI 어댑터 계획을 요약해줘"
```

실행이 끝나면 `workspace/runs/<run-id>/summary.md` 경로가 출력되고, 각 task별 `input.md`, `result.md`, `metadata.json`도 같은 run 폴더 아래에 저장된다.

## Order Pickup API

외부 프론트가 요청을 먼저 접수하고, 나중에 주문번호(`order_id`)로 결과를 찾아가는 흐름도 지원한다.

구조:

`POST /orders` -> `workspace/runs/<order_id>/status.json` 생성 -> 워커가 실행 -> `summary.md` 생성 -> 파일 또는 API로 수령

주문번호는 곧바로 `workspace/runs/<order_id>/` 폴더명으로 사용된다.

### 1) API 서버 실행

```bash
uv run inhouse-crew api --host 127.0.0.1 --port 8000
```

### 2) 워커 실행

지속 실행:

```bash
uv run inhouse-crew worker
```

한 건만 처리:

```bash
uv run inhouse-crew worker --once
```

### 3) 주문 접수

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "crew_id": "quickstart",
    "user_request": "로컬 Codex 세션을 사용하는 CrewAI 어댑터 계획을 요약해줘"
  }'
```

응답 예시:

```json
{
  "order_id": "T20260307-000001_로컬-Codex-세션을-사용하는",
  "status": "queued",
  "status_url": "/orders/T20260307-000001_로컬-Codex-세션을-사용하는/status",
  "pickup_url": "/pickup/T20260307-000001_로컬-Codex-세션을-사용하는",
  "summary_file": "/abs/path/workspace/runs/T20260307-000001_로컬-Codex-세션을-사용하는/summary.md",
  "requested_at": "2026-03-07T12:00:00+00:00"
}
```

### 4) 상태 조회

```bash
curl http://127.0.0.1:8000/orders/<order_id>/status
```

`status.json` 기준으로 `queued`, `running`, `completed`, `failed` 상태를 확인할 수 있다.

### 5) 결과 수령 시나리오 A: 파일 직접 접근

완료 후 프론트가 공유 스토리지에 직접 접근할 수 있다면 아래 파일을 읽으면 된다.

```bash
cat workspace/runs/<order_id>/summary.md
```

이 방식은 가장 단순하고, `summary.md` 가 최종 산출물 기준 파일이다.

### 6) 결과 수령 시나리오 B: pickup API

파일 직접 접근 대신 같은 결과를 API로 받을 수도 있다.

```bash
curl http://127.0.0.1:8000/pickup/<order_id>
```

동작:

- `completed`: `summary.md` 를 `text/markdown` 으로 반환
- `queued` / `running`: `202 Accepted`
- `failed`: `409 Conflict`
- 주문번호 없음: `404 Not Found`

현재는 파일 직접 접근과 pickup API를 **둘 다 열어둔 실험 단계**다. 프론트에서 어떤 방식이 더 맞는지 실제 연결 후 결정하면 된다.

## Config Layout

- `configs/agents/*.yaml`: agent persona 정의
- `configs/crews/*.yaml`: crew/task 흐름 정의
- `configs/settings.yaml`: Codex/workspace 기본 설정

## Agent Persona Example

README에는 persona 파일 예제를 1개만 유지한다. 다른 persona는 `configs/agents/` 경로의 실제 YAML을 기준으로 확인한다.

```yaml
id: game_concept_generator
role: Game Concept Generator
goal: 독창적이고 명확한 게임 컨셉 초안을 만든다.
backstory: >
  당신은 새로운 게임 아이디어를 빠르게 발굴하고, 강한 테마와 플레이 동기를
  중심으로 초기 방향을 제시하는 창의적인 게임 디렉터다.
rules:
  - 장르, 핵심 테마, 기본적인 게임 플레이 루프, 플레이어 동기를 반드시 포함한다.
  - 독창성과 명확성을 우선한다.
  - 이 단계에서는 복잡한 시스템이나 세부 메커니즘을 확장하지 않는다.
  - 강력한 출발점이 되는 게임 컨셉 제안에 집중한다.
allow_delegation: false
verbose: true
llm: codex-local-oauth
tools: []
```

## Status

부트스트랩 구현과 기본 검증은 완료됐다. 현재 문서는 [docs/inhouse-crew-bootstrap-implementation.md](/Users/sean/Documents/InhouseCrew/docs/inhouse-crew-bootstrap-implementation.md)에 정리되어 있고, `quickstart`, `coding_session`, `review_session`, `feature_delivery`, `product_discovery`, `game_design_team` crew 샘플을 바로 실행할 수 있다.
