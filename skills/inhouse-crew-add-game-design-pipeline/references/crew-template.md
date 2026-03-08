# Crew Template

Use this shape for config-driven game design crews.

```yaml
id: sample_game_design_team
name: Sample Game Design Team Crew
process: sequential
agents:
  - game_concept_generator
  - game_fantasy_designer
  - game_innovation_designer
  - game_market_validator
  - game_design_director
tasks:
  - id: generate_game_concept
    agent: game_concept_generator
    description: >
      입력 요구사항 `{user_request}`를 바탕으로 초기 게임 컨셉을 만든다.
    expected_output: >
      초기 게임 컨셉이 담긴 Markdown 문서.
    output_artifact: concept.md
output_policy:
  save_markdown: true
  include_metadata: true
```

Checklist:

- `process` 는 기본적으로 `sequential`
- task 순서는 사고 흐름과 일치해야 함
- 각 task는 고유한 `output_artifact` 를 가져야 함
- 최종 종합 문서가 필요하면 synthesis task를 별도로 둠
- `src/inhouse_crew/domain/` wrapper는 추가하지 않음
