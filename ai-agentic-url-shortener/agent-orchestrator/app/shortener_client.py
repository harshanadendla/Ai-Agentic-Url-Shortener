from __future__ import annotations

import uuid

import httpx

from app.config import settings


class ShortenerClient:
    """Cross-language integration boundary used by the release validation agent."""

    def smoke_test(self) -> dict[str, object]:
        base = settings.shortener_base_url.rstrip("/")
        alias = "agt" + uuid.uuid4().hex[:9]
        with httpx.Client(timeout=8.0, follow_redirects=False) as client:
            health = client.get(f"{base}/actuator/health")
            health.raise_for_status()
            created = client.post(f"{base}/api/v1/links", json={"url": "https://example.com/agent-validation", "customAlias": alias})
            created.raise_for_status()
            redirect = client.get(f"{base}/{alias}")
            if redirect.status_code != 307 or redirect.headers.get("location") != "https://example.com/agent-validation":
                raise RuntimeError("Java redirect contract validation failed")
            analytics = client.get(f"{base}/api/v1/links/{alias}/analytics")
            analytics.raise_for_status()
            payload = analytics.json()
            if payload.get("clicks", 0) < 1:
                raise RuntimeError("analytics counter did not increment")
            client.delete(f"{base}/api/v1/links/{alias}").raise_for_status()
            return {
                "health": health.json().get("status"),
                "create_status": created.status_code,
                "redirect_status": redirect.status_code,
                "analytics_clicks": payload.get("clicks"),
                "deactivated": True,
            }
