from __future__ import annotations

from crewai import Crew

from ..crew_factory import CrewFactory


def create_planning_crew(factory: CrewFactory) -> Crew:
    return factory.create_crew("product_discovery")
