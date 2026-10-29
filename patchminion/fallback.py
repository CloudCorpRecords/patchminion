"""Deterministic keyword triage — the clearly-labeled STUB.

This module exists so the full pipeline (fixture → verdicts → report) runs
with no model credentials at all, e.g. in CI or for a first smoke test. It is
keyword scoring only; it does NOT call a model and its output is always
marked ``source="fallback"`` so a stub run can never be mistaken for a real
model-backed run. Set a provider key for OpenMinion (see README) to get real
``source="model"`` verdicts through the exact same code path.
"""

from __future__ import annotations

import re

from .models import Issue, Triage

_CATEGORY_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bug", ("crash", "error", "exception", "traceback", "fails", "broken",
             "regression", "stack trace", "won't", "bug", "slow",
             "performance", "hangs", "freezes", "vulnerab", "plaintext",
             "leak")),
    ("question", ("how do i", "how to", "is it possible", "question",
                  "help", "why does", "what is")),
    ("docs", ("docs", "documentation", "readme", "typo", "guide",
              "tutorial", "example")),
    ("chore", ("bump", "dependency", "dependencies", "ci", "upgrade",
               "deprecat", "refactor", "cleanup")),
    ("feature", ("feature", "add support", "request", "would be nice",
                 "suggestion", "please add", "enhancement")),
)

_LABEL_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("crash", ("crash", "traceback", "stack trace", "exception")),
    ("regression", ("regression", "since v", "used to work", "broke in")),
    ("performance", ("slow", "performance", "memory", "cpu", "latency")),
    ("security", ("security", "vulnerability", "cve", "xss", "injection")),
    ("ui", ("ui", "button", "layout", "screen", "dark mode", "render")),
    ("api", ("api", "endpoint", "webhook", "sdk")),
    ("needs-repro", ("sometimes", "intermittent", "randomly", "occasionally")),
    ("good-first-issue", ("typo", "docs", "documentation", "readme")),
)

_PRIORITY_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("P0", ("data loss", "security", "vulnerability", "outage")),
    ("P1", ("crash", "fails", "broken", "regression")),
    ("P3", ("typo", "minor", "cosmetic", "nice to have")),
)

_CATEGORY_LABEL = {
    "bug": "bug",
    "feature": "enhancement",
    "question": "question",
    "docs": "documentation",
    "chore": "chore",
}


def _matches(text: str, signal: str) -> bool:
    # Match at a word start only: "crash" matches "crashes", but "ui" does
    # not match inside "quickstart" and "bug" does not match inside "debug".
    return re.search(r"\b" + re.escape(signal), text) is not None


def _score(text: str, signals: tuple[str, ...]) -> int:
    return sum(1 for s in signals if _matches(text, s))


def classify_issue(issue: Issue) -> Triage:
    """Classify one issue with deterministic keyword scoring."""
    text = f"{issue.title}\n{issue.body}".lower()

    category, best = "question", 0
    for name, signals in _CATEGORY_SIGNALS:
        score = _score(text, signals)
        if score > best:
            category, best = name, score

    labels = [_CATEGORY_LABEL[category]]
    if category == "chore":
        labels = ["enhancement"]  # no "chore" label in the vocabulary
    for label, signals in _LABEL_SIGNALS:
        if label not in labels and _score(text, signals) > 0:
            labels.append(label)
    labels = labels[:4]

    priority = "P2"
    for level, signals in _PRIORITY_SIGNALS:
        if _score(text, signals) > 0:
            priority = level
            break
    if category == "chore" and priority == "P0":
        priority = "P1"  # a dependency bump is urgent, not an active incident

    summary = (issue.body.strip().split(".")[0] or issue.title).strip()
    if len(summary) > 140:
        summary = summary[:137].rsplit(" ", 1)[0] + "..."
    first_response = (
        f"Thanks for the report! Triage (automated stub): this looks like a "
        f"{category} ({priority}). A maintainer will confirm the suggested "
        f"labels: {', '.join(labels)}."
    )
    return Triage(
        issue_number=issue.number,
        category=category,
        labels=labels,
        priority=priority,
        summary=summary,
        first_response=first_response,
        source="fallback",
    )
