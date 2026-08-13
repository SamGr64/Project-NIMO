from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from nimo.reporting.schemas import ReportNarrative


class OpenAINarrativeProvider:
    name = "openai"

    def __init__(self, *, prompts_root: Path, api_key: str | None = None) -> None:
        self.prompts_root = prompts_root
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def generate(self, evidence: dict[str, Any], *, model: str | None = None) -> ReportNarrative:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install Project NIMO with the reports extra to use OpenAI") from exc
        system = (self.prompts_root / "report_system.md").read_text(encoding="utf-8")
        request = (self.prompts_root / "report_request.md").read_text(encoding="utf-8")
        client = OpenAI(api_key=self.api_key)
        response = client.responses.parse(
            model=model or "gpt-5-mini",
            input=[
                {"role": "developer", "content": system},
                {
                    "role": "user",
                    "content": request + "\n\nStructured NIMO evidence:\n" + json.dumps(evidence, sort_keys=True, default=str),
                },
            ],
            text_format=ReportNarrative,
        )
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise RuntimeError("OpenAI did not return a parsed report narrative")
        return parsed
