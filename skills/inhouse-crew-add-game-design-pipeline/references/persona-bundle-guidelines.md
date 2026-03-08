# Persona Bundle Guidelines

기존 persona를 우선 재사용한다.

새 persona를 추가해야 하는 경우:

- pipeline의 마지막 단계가 단순 검토가 아니라 종합 결론 작성인 경우
- 기존 persona 중 어떤 것도 최종 역할을 자연스럽게 수행하지 못하는 경우
- 앞선 여러 산출물을 하나의 방향성 문서로 통합해야 하는 경우

기존 persona만으로 충분한 경우:

- 마지막 단계가 기존 `reviewer` 또는 기존 specialist의 확장 역할로 충분한 경우
- 산출물이 단계별 문서만 필요하고 별도 synthesis 문서가 필요 없는 경우

동기화 규칙:

- 새 persona를 추가하면 `tests/test_persona_loader.py` 를 갱신
- 새 crew를 추가하면 `tests/test_persona_loader.py` 와 `tests/test_crew_factory.py` 를 함께 갱신
- README는 single persona example 정책을 유지
