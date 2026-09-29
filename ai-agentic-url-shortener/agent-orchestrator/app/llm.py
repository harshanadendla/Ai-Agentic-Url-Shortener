from __future__ import annotations

import httpx

from app.config import settings


class LocalLLM:
    """Optional local-model boundary. Deterministic orchestration remains functional without a model."""

    def complete(self, prompt: str) -> str | None:
        if not settings.llm_enabled:
            return None
        try:
            response = httpx.post(
                f"{settings.ollama_url.rstrip('/')}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
                timeout=20.0,
            )
            response.raise_for_status()
            text = response.json().get("response", "").strip()
            return text or None
        except (httpx.HTTPError, ValueError):
            return None
