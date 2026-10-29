"""Parse a model reply into a validated :class:`Triage` (pure logic).

PatchMinion asks the model for exactly one JSON object per batch. Models do
not always comply, so this parser is deliberately defensive: it extracts the
first balanced JSON object from the reply text, then validates every field
against the closed vocabularies in :mod:`patchminion.models`. Anything that
fails validation raises ``ValueError`` with a specific reason, and the caller
falls back to the deterministic stub for that issue instead of guessing.
"""

from __future__ import annotations

import json

from .models import CATEGORIES, LABEL_VOCABULARY, PRIORITIES, Triage


def extract_json_object(text: str) -> dict:
    """Return the first balanced ``{...}`` JSON object found in ``text``."""
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in model reply")
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(text[start : idx + 1])
                except json.JSONDecodeError as exc:
                    raise ValueError(f"unparseable JSON object: {exc}") from exc
                if not isinstance(obj, dict):
                    raise ValueError("JSON payload is not an object")
                return obj
    raise ValueError("unterminated JSON object in model reply")


def parse_triage(text: str, issue_number: int) -> Triage:
    """Parse one issue's verdict out of a model reply.

    Accepts a bare verdict object, ``{"triage": [ {...}, ... ]}``, or the
    same shape under an ``"issues"`` key. A bare object with no
    ``issue_number`` is attributed to the requested issue (the turn asked
    for exactly one issue); a named but different issue is still rejected.
    Raises ``ValueError`` on any schema/vocabulary violation.
    """
    obj = extract_json_object(text)
    entries = obj.get("triage", obj.get("issues"))
    if entries is None:
        entries = [obj]
    if not isinstance(entries, list):
        raise ValueError("'triage' is not a list")
    # A bare verdict object with no issue_number, in a turn that asked for
    # exactly one issue, is that issue's verdict: the turn's issue is
    # unambiguous, and every field below is still validated. A bare object
    # that names a different issue still fails to match and is rejected.
    if (
        len(entries) == 1
        and entries[0] is obj
        and isinstance(obj, dict)
        and "issue_number" not in obj
        and "category" in obj
    ):
        entries = [dict(obj, issue_number=issue_number)]
    match = None
    for entry in entries:
        if isinstance(entry, dict) and int(entry.get("issue_number", -1)) == issue_number:
            match = entry
            break
    if match is None:
        raise ValueError(f"no verdict for issue #{issue_number} in model reply")

    category = str(match.get("category", "")).strip().lower()
    if category not in CATEGORIES:
        raise ValueError(f"category {category!r} not in {CATEGORIES}")
    priority = str(match.get("priority", "")).strip().upper()
    if priority not in PRIORITIES:
        raise ValueError(f"priority {priority!r} not in {PRIORITIES}")
    labels_raw = match.get("labels", [])
    if not isinstance(labels_raw, list):
        raise ValueError("'labels' is not a list")
    labels = [str(x).strip().lower() for x in labels_raw]
    unknown = [x for x in labels if x not in LABEL_VOCABULARY]
    if unknown:
        raise ValueError(f"labels outside vocabulary: {unknown}")
    # The category label itself is always suggested (feature maps to
    # "enhancement"); never insert it twice if the model already gave it.
    category_label = category if category != "feature" else "enhancement"
    if category_label not in labels:
        labels.insert(0, category_label)

    triage = Triage(
        issue_number=issue_number,
        category=category,
        labels=labels,
        priority=priority,
        summary=str(match.get("summary", "")).strip(),
        first_response=str(match.get("first_response", "")).strip(),
        source="model",
    )
    problems = triage.validate()
    if problems:
        raise ValueError("; ".join(problems))
    return triage
