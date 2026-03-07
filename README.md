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

## Config Layout

- `configs/agents/*.yaml`: agent persona 정의
- `configs/crews/*.yaml`: crew/task 흐름 정의
- `configs/settings.yaml`: Codex/workspace 기본 설정

## Status

부트스트랩 구현과 기본 검증은 완료됐다. 현재 문서는 [docs/inhouse-crew-bootstrap-implementation.md](/Users/sean/Documents/InhouseCrew/docs/inhouse-crew-bootstrap-implementation.md)에 정리되어 있고, `quickstart`, `coding_session`, `review_session`, `feature_delivery`, `product_discovery` crew 샘플을 바로 실행할 수 있다.
