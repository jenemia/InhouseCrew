# Persona Template

Use this order unless the repository schema changes.

```yaml
id: sample_persona
role: Sample Role
goal: 한 줄 목표
backstory: >
  두 줄 이하의 정체성 설명.
rules:
  - 핵심 출력 조건 1
  - 핵심 출력 조건 2
allow_delegation: false
verbose: true
llm: codex-local-oauth
tools: []
```

Checklist:

- `id` 는 `snake_case`
- `goal` 은 한 문장으로 유지
- `backstory` 는 정체성만 설명하고 구현 세부는 넣지 않기
- `rules` 에 필수 출력 요소와 금지 사항만 넣기
- `tests/test_persona_loader.py` 기대값 동기화
- `README.md` persona 예제는 1개만 유지
