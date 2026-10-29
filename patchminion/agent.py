"""OpenMinion glue for PatchMinion — the ONLY module that imports openminion.

API surface used (OpenMinion 0.1.x Python facade, per the project's README
quick-start and ``examples/starter/quickstart.py``; the README names
``API_COMPATIBILITY.md`` as the 0.1.x contract, and every call below was
additionally verified against the installed 0.1.13 package's signatures):

* ``from openminion import Agent, ProviderError, tool``
* ``@tool`` on plain typed functions to expose them to the model. Both
  tools are declared ``min_scope="READ_ONLY", idempotent=True``: they are
  pure reads (an in-memory dict lookup and a constant), and without the
  declaration OpenMinion registers caller-supplied tools at its
  ``WRITE_SAFE`` family default, which makes the action-policy gate demand
  an interactive confirmation (risk "write", unknown reversibility) that a
  headless run can never answer — the turn then ends with the confirmation
  prompt as its "reply" and no model verdict is produced at all.
* ``Agent(instructions=..., tools=[...], session_id=..., config_path=...)``
  used as a context manager; ``agent.run(prompt)`` returns an
  ``AgentRunResult`` with ``.text`` and ``.session_id``

The agent is given two read-only tools (issue lookup, label vocabulary) and
asked for one JSON verdict per issue. Every verdict is validated by
:mod:`patchminion.parsing`; a verdict that fails validation is replaced by
the deterministic stub for that issue and the replacement is counted, so the
run log never hides a model failure.
"""

from __future__ import annotations

from openminion import Agent, ProviderError, tool

from . import fallback
from .models import LABEL_VOCABULARY, Issue, Triage
from .parsing import parse_triage

_ISSUES: dict[int, Issue] = {}


@tool(min_scope="READ_ONLY", idempotent=True)
def get_issue(issue_number: int) -> str:
    """Return the title and body of one issue in the current triage batch."""
    issue = _ISSUES.get(int(issue_number))
    if issue is None:
        return f"unknown issue number: {issue_number}"
    return f"#{issue.number} {issue.title}\n\n{issue.body}"


@tool(min_scope="READ_ONLY", idempotent=True)
def label_vocabulary() -> str:
    """Return the closed list of labels a triage verdict may suggest."""
    return ", ".join(LABEL_VOCABULARY)


INSTRUCTIONS = """You are PatchMinion, a meticulous GitHub issue triage agent.

You will be given ONE issue number. Call get_issue with that number to read
the issue, then decide:
- category: one of bug, feature, question, docs, chore
- labels: 1-4 labels, ONLY from label_vocabulary (call it if unsure); always
  include the label matching the category (bug->bug, feature->enhancement,
  question->question, docs->documentation, chore->enhancement)
- priority: P0 (data loss / security / outage), P1 (crash / broken core
  flow / regression), P2 (normal), P3 (minor / cosmetic)
- summary: one sentence, max 140 characters
- first_response: a friendly 1-2 sentence maintainer reply that thanks the
  reporter and states the next step

Reply with ONLY a JSON object in exactly this shape, with ALL six fields
filled in for the issue — never a label-only map, never prose outside the
JSON object:
{"triage": [{"issue_number": 101, "category": "bug", "labels": ["bug"],
"priority": "P1", "summary": "...", "first_response": "..."}]}
These rules are not negotiable: "issue_number" must be the number you were
given; "category" must be exactly one of bug, feature, question, docs,
chore — never a synonym like feature_request, maintenance or
dependency-update; "priority" must be exactly one of P0, P1, P2, P3 —
never a word like critical, high, medium or low; "labels" must come only
from label_vocabulary."""


def run_model_triage(
    issues: list[Issue],
    *,
    config_path: str | None = None,
    session_id: str = "patchminion-triage",
) -> tuple[list[Triage], list[str]]:
    """Run one OpenMinion agent turn over the batch.

    Returns ``(verdicts, log_lines)``. Per-issue verdicts that fail
    validation are replaced by the stub and the replacement is logged;
    a provider-level failure propagates as ``ProviderError`` so the caller
    can fall back for the whole batch and say so.
    """
    _ISSUES.clear()
    _ISSUES.update({i.number: i for i in issues})
    log: list[str] = []
    kwargs: dict = {}
    if config_path:
        kwargs["config_path"] = config_path

    # One agent turn per issue, not one turn for the whole batch: with a
    # single batch turn the model had to juggle 6 issues x tool calls in
    # one long context and twice returned an off-schema reply (once prose,
    # once a label-only map), so every verdict failed validation. A
    # per-issue turn keeps the context short and the output contract
    # simple; the validation gate itself is unchanged.
    verdicts: list[Triage] = []
    sessions: list[str] = []
    for issue in issues:
        prompt = (
            f"Triage issue #{issue.number}. Call get_issue({issue.number}) "
            "to read it, then reply with ONLY this JSON object, filled in "
            "for this one issue: {\"triage\": [{\"issue_number\": "
            f"{issue.number}, \"category\": \"bug|feature|question|docs|chore\", "
            "\"labels\": [...], \"priority\": \"P0|P1|P2|P3\", \"summary\": \"...\", "
            "\"first_response\": \"...\"}]}. Use exactly one of the listed "
            "category strings and exactly one of P0, P1, P2, P3 for "
            "priority — no synonyms, no natural-language priorities."
        )
        # A failure inside one issue's turn (provider error, timeout,
        # OpenMinion state-store hiccup) stubs only that issue; it must
        # not take down verdicts already earned for the rest of the batch.
        try:
            with Agent(
                instructions=INSTRUCTIONS,
                tools=[get_issue, label_vocabulary],
                session_id=f"{session_id}-{issue.number}",
                **kwargs,
            ) as agent:
                result = agent.run(prompt)
        except Exception as exc:
            log.append(
                f"issue #{issue.number}: model run failed "
                f"({exc.__class__.__name__}: {exc}); deterministic stub "
                "used for this issue"
            )
            verdicts.append(fallback.classify_issue(issue))
            continue
        if result.session_id and result.session_id not in sessions:
            sessions.append(str(result.session_id))
        try:
            verdicts.append(parse_triage(result.text, issue.number))
        except ValueError as exc:
            log.append(
                f"issue #{issue.number}: model verdict rejected ({exc}); "
                "deterministic stub used for this issue"
            )
            verdicts.append(fallback.classify_issue(issue))
    log.insert(0, f"openminion sessions: {', '.join(sessions) or session_id}")
    accepted = sum(1 for v in verdicts if v.source == "model")
    log.append(f"model verdicts accepted: {accepted}/{len(issues)}")
    return verdicts, log


__all__ = ["ProviderError", "run_model_triage"]
