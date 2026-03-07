inhouse_crew/
├─ pyproject.toml
├─ .env
├─ configs/
│  ├─ agents/
│  │  ├─ planner.yaml
│  │  ├─ architect.yaml
│  │  ├─ developer.yaml
│  │  └─ reviewer.yaml
│  ├─ crews/
│  │  ├─ product_discovery.yaml
│  │  └─ feature_delivery.yaml
│  └─ settings.yaml
├─ src/
│  └─ inhouse_crew/
│     ├─ main.py
│     ├─ crew_factory.py
│     ├─ persona_loader.py
│     ├─ task_workspace.py
│     ├─ llms/
│     │  └─ codex_cli_llm.py
│     ├─ tools/
│     │  ├─ file_ops.py
│     │  └─ official_tools.py
│     └─ domain/
│        ├─ planning_crew.py
│        ├─ coding_crew.py
│        └─ review_crew.py
└─ workspace/
   └─ runs/



   각 모듈의 책임
llms/codex_cli_llm.py

책임:

CrewAI가 사용할 custom LLM 구현

로컬 Codex provider 호출

timeout / retry / error handling

금지:

task 폴더 생성

persona 해석

임의의 파일 저장 정책 결정

persona_loader.py

책임:

YAML 로딩

schema 검증

Agent 생성용 데이터 변환

금지:

subprocess 실행

workspace 생성

Codex provider 직접 호출

task_workspace.py

책임:

run 디렉터리 생성

task 디렉터리 생성

.md 결과 저장

metadata 저장

금지:

Agent 생성

LLM 선택

persona 로직 처리

crew_factory.py

책임:

persona + llm + tools + task를 조합

crew 인스턴스 생성

도메인별 crew 구성

금지:

vendor 코드 수정

task 파일 저장 세부규칙 직접 소유