from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class CategoryDefinition:
    slug: str
    label: str
    direction: str
    keywords: tuple[str, ...]
    parent_slug: str | None = None


def iter_category_definitions(config: dict[str, Any]) -> Iterator[CategoryDefinition]:
    for slug, payload in config.get("categories", {}).items():
        direction = str(payload.get("direction", "either"))
        yield CategoryDefinition(
            slug=str(slug),
            label=str(payload.get("label", slug.replace("_", " ").title())),
            direction=direction,
            keywords=tuple(str(value).lower() for value in payload.get("keywords", [])),
        )
        for child_slug, child_payload in payload.get("children", {}).items():
            yield CategoryDefinition(
                slug=str(child_slug),
                label=str(child_payload.get("label", child_slug.replace("_", " ").title())),
                direction=str(child_payload.get("direction", direction)),
                keywords=tuple(
                    str(value).lower() for value in child_payload.get("keywords", [])
                ),
                parent_slug=str(slug),
            )
