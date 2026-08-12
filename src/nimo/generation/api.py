from __future__ import annotations

from typing import TYPE_CHECKING

from nimo.domain.models import GenerationRequest, GenerationResult

if TYPE_CHECKING:
    from nimo.application.container import ApplicationContainer


def generate_user_statements(
    container: "ApplicationContainer",
    request: GenerationRequest,
) -> GenerationResult:
    return container.generation.generate(request)
