from __future__ import annotations

from crewai import Crew

from ..crew_factory import CrewFactory


def create_coding_crew(factory: CrewFactory) -> Crew:
    return factory.create_crew("coding_session")
