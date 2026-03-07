# INHOUSE_CREW_AGENT_GUIDE.md

## 목적
이 프로젝트의 목적은 CrewAI 프레임워크(https://github.com/crewAIInc/crewAI)를 **원본 수정 없이** 상위 레이어에서 확장하여, 나만의 인하우스 Crew를 구축하는 것이다.

이 문서는 모든 에이전트와 상위 오케스트레이터가 따라야 하는 공통 지침이다.

---

## 최상위 원칙

### 1. 원본 불변
- `crewai` 및 관련 원본 스크립트는 절대 수정하지 않는다.
- monkey patch, 내부 private API 수정, vendor source patch를 금지한다.
- 필요한 기능은 모두 상위 레이어에서 구현한다.

### 2. 상위 레이어 확장
- 공식 확장 포인트가 있으면 그것을 사용한다.
- 공식 기능이 부족하면 adapter, wrapper, manager, factory 형태로 구현한다.
- 구현 책임은 아래 레이어로 분리한다.
  - configuration layer
  - composition layer
  - adapter layer
  - workspace layer

### 3. 공식 기술 우선
- 무언가를 만들 때 공식 기술 문서를 먼저 참고한다.
- 공식적으로 지원되는 방식이 있으면 반드시 그 방식을 우선 사용한다.
- 공식 지원이 없는 경우에만 상위 레이어 custom 구현을 한다.
- “편해서 내부 수정”은 금지한다.

### 4. 산출물 중심
- 모든 작업은 재사용 가능한 산출물 중심으로 남긴다.
- 각 Task는 폴더를 가지며, 하위에 `.md` 결과 문서를 생성한다.
- 모든 출력은 사람이 검토할 수 있는 Markdown 문서를 우선한다.

---

## 이번 스펙의 필수 구현 범위

이 프로젝트는 아래 3가지를 처음부터 구축해야 한다.

### 1) 로컬 OAuth Codex 세션을 범용 LLM provider처럼 사용할 수 있는 Custom LLM
목표:
- CrewAI agent가 일반 LLM처럼 사용할 수 있는 custom LLM adapter를 만든다.
- 로컬 환경에서 로그인된 Codex CLI 또는 Codex provider를 상위 레이어에서 감싼다.
- CrewAI 원본은 수정하지 않는다.

규칙:
- CrewAI의 공식 Custom LLM 확장 포인트를 우선 사용한다.
- Codex OAuth 세션을 직접 해킹하거나 내부 토큰 구조에 의존하지 않는다.
- 로컬 실행기 또는 래퍼 계층에서 인증된 Codex 세션을 사용한다.
- CrewAI에는 “입력 → 출력” 형태의 LLM 인터페이스만 노출한다.

금지:
- CrewAI 내부 클래스 수정
- vendor 코드 패치
- private API 의존
- 원본 패키지 소스 변경

권장 구현 방향:
- `CodexCliLLM` 또는 동등한 custom LLM adapter를 작성한다.
- 내부에서는 로컬 Codex provider를 호출한다.
- timeout, retry, error handling을 adapter 계층에서 처리한다.
- 파일 수정이나 shell 실행 책임은 LLM이 아니라 별도 tool 또는 workflow에 둔다.

---

### 2) 각 Agent에 persona를 YAML로 지정할 수 있는 구조
목표:
- 각 agent의 역할, 목표, 배경, 규칙, 도구, 기본 LLM을 YAML로 정의한다.
- 코드에서는 YAML을 읽어 Agent를 조립한다.
- persona 변경이 코드 수정 없이 가능해야 한다.

필수 조건:
- persona는 데이터다.
- persona YAML은 코드와 분리한다.
- Agent 생성은 loader/factory가 담당한다.
- LLM 선택과 tool 연결도 persona 또는 상위 설정에서 관리한다.

권장 YAML 필드:
- `id`
- `role`
- `goal`
- `backstory`
- `rules`
- `allow_delegation`
- `verbose`
- `llm`
- `tools`

예시 구조:
```yaml
id: planner
role: "Product Planning Strategist"
goal: "요구사항을 명확한 작업 단위로 분해한다"
backstory: >
  당신은 서비스 기획과 기술 협업 경험이 풍부한 PM이다.
rules:
  - "원본 코드를 직접 수정하라고 지시하지 않는다"
  - "공식 문서를 우선 참고한다"
  - "불확실한 내용은 추정하지 말고 명시한다"
allow_delegation: false
verbose: true
llm: "codex-local-oauth"
tools:
  - "file_read"
  - "file_write"