"""Render triage verdicts as a Markdown report and a JSON run log (pure)."""

from __future__ import annotations

import hashlib
import json

from .models import Issue, Triage


def fixture_fingerprint(issues: list[Issue]) -> str:
    """Stable short hash of the batch — the reproducibility anchor."""
    payload = json.dumps(
        [
            {"number": i.number, "title": i.title, "body": i.body,
             "labels": list(i.labels)}
            for i in issues
        ],
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def render_markdown(
    issues: list[Issue],
    verdicts: list[Triage],
    *,
    mode: str,
    log: list[str],
) -> str:
    by_number = {i.number: i for i in issues}
    model_count = sum(1 for v in verdicts if v.source == "model")
    lines = [
        "# PatchMinion triage report",
        "",
        f"- Mode: **{mode}** "
        f"({'model-backed' if mode == 'model' else 'deterministic stub — NOT a model run'})",
        f"- Issues: {len(issues)} · fixture fingerprint: "
        f"`{fixture_fingerprint(issues)}`",
        f"- Verdicts from the model: {model_count}/{len(verdicts)}",
        "",
        "| Issue | Category | Priority | Labels | Source |",
        "|---|---|---|---|---|",
    ]
    for v in verdicts:
        title = by_number[v.issue_number].title.replace("|", "\\|")
        lines.append(
            f"| #{v.issue_number} {title} | {v.category} | {v.priority} | "
            f"{', '.join(v.labels)} | {v.source} |"
        )
    lines += ["", "## Details", ""]
    for v in verdicts:
        lines += [
            f"### Issue #{v.issue_number} — {by_number[v.issue_number].title}",
            "",
            f"- **Summary:** {v.summary}",
            f"- **Suggested first response:** {v.first_response}",
            "",
        ]
    if log:
        lines += ["## Run log", ""] + [f"- {entry}" for entry in log] + [""]
    return "\n".join(lines)


def render_json_log(
    issues: list[Issue],
    verdicts: list[Triage],
    *,
    mode: str,
    log: list[str],
) -> str:
    return json.dumps(
        {
            "tool": "patchminion",
            "mode": mode,
            "fixture_fingerprint": fixture_fingerprint(issues),
            "log": log,
            "triage": [v.to_dict() for v in verdicts],
        },
        indent=2,
    )
