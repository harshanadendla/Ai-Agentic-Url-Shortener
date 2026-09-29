from __future__ import annotations

import re
from pathlib import Path

from app.config import settings


class JavaRepositoryInspector:
    def __init__(self, root: Path | None = None):
        self.root = (root or settings.shortener_repo_root).resolve()

    def impacted_files(self, requirement: str) -> list[str]:
        if not self.root.exists():
            return []
        tokens = {t for t in re.findall(r"[a-zA-Z]{4,}", requirement.lower()) if t not in {"with", "from", "that", "this", "make", "better"}}
        tokens |= {"link", "short", "url", "analytics", "click", "cache", "schema", "redirect", "rate", "limit"}
        scored: list[tuple[int, str]] = []
        for path in self.root.rglob("*"):
            if not path.is_file() or path.suffix not in {".java", ".xml", ".yml", ".yaml", ".sql"}:
                continue
            body = path.read_text(encoding="utf-8", errors="ignore").lower()
            score = sum(1 for token in tokens if token in body or token in path.name.lower())
            if score:
                scored.append((score, str(path.relative_to(self.root))))
        return [name for _, name in sorted(scored, key=lambda x: (-x[0], x[1]))[:12]]

    def architecture_facts(self) -> dict[str, object]:
        java_files = list((self.root / "src").rglob("*.java")) if (self.root / "src").exists() else []
        return {
            "repo_root": str(self.root),
            "java_file_count": len(java_files),
            "has_maven": (self.root / "pom.xml").exists(),
            "has_flyway": (self.root / "src/main/resources/db/migration").exists(),
            "framework": "Spring Boot / Spring MVC / Spring Data JPA / Spring Data Redis",
        }
