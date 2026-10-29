"""Data model and fixture loading for PatchMinion (pure logic, no I/O beyond
reading the fixture file the caller names)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CATEGORIES = ("bug", "feature", "question", "docs", "chore")
PRIORITIES = ("P0", "P1", "P2", "P3")

# The label vocabulary PatchMinion is allowed to suggest. Keeping this closed
# makes triage output reviewable and the demo reproducible.
LABEL_VOCABULARY = (
    "bug",
    "enhancement",
    "question",
    "documentation",
    "crash",
    "regression",
    "performance",
    "security",
    "ui",
    "api",
    "needs-repro",
    "good-first-issue",
)


@dataclass(frozen=True)
class Issue:
    """One GitHub issue to triage."""

    number: int
    title: str
    body: str = ""
    labels: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict) -> "Issue":
        return cls(
            number=int(raw["number"]),
            title=str(raw["title"]),
            body=str(raw.get("body", "")),
            labels=tuple(str(x) for x in raw.get("labels", ())),
        )


@dataclass
class Triage:
    """The triage verdict for one issue."""

    issue_number: int
    category: str
    labels: list[str] = field(default_factory=list)
    priority: str = "P2"
    summary: str = ""
    first_response: str = ""
    source: str = "model"  # "model" (OpenMinion run) or "fallback" (stub)

    def validate(self) -> list[str]:
        """Return a list of problems with this verdict (empty = valid)."""
        problems: list[str] = []
        if self.category not in CATEGORIES:
            problems.append(f"bad category: {self.category!r}")
        if self.priority not in PRIORITIES:
            problems.append(f"bad priority: {self.priority!r}")
        unknown = [x for x in self.labels if x not in LABEL_VOCABULARY]
        if unknown:
            problems.append(f"labels outside vocabulary: {unknown}")
        return problems

    def to_dict(self) -> dict:
        return asdict(self)


def load_issues(path: str | Path) -> list[Issue]:
    """Load issues from a JSON fixture: a list of {number, title, body, labels}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("fixture must be a JSON list of issues")
    issues = [Issue.from_dict(raw) for raw in data]
    numbers = [i.number for i in issues]
    if len(set(numbers)) != len(numbers):
        raise ValueError(f"duplicate issue numbers in fixture: {numbers}")
    return issues
