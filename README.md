# PatchMinion — a reproducible GitHub-issue triage agent

**Cortensor Hackathon #5 entry.** PatchMinion triages a batch of GitHub
issues with the **OpenMinion 0.1 Python SDK**: for each issue it decides a
category, suggests labels from a closed vocabulary, assigns a priority,
writes a one-line summary, and drafts a first maintainer response. The model
proposes; deterministic code disposes — every model verdict is parsed and
validated, and anything invalid is rejected, replaced, and logged.

## Build Disclosure

Built by AI agents (Tree / Muse fleet) directed by Rene Turcios, for
Cortensor Hackathon #5. AI-assisted development is explicitly allowed by the
hackathon rules; this disclosure is included voluntarily and matches the
honesty labeling inside the tool itself: PatchMinion marks every verdict
with where it actually came from (`model` vs `fallback`).

## Live-run status (read this first)

**Live model run, 2026-10-28.** The model path has now been executed
against a hosted model: Fireworks `accounts/fireworks/models/glm-5p3-flash`
via the pack's local `fw-proxy` (provider slot `openai` →
`http://127.0.0.1:8791/inference/v1`; the proxy attaches the real
credential, so no key is committed or printed here). The shipped
`examples/expected-output-model.md` is that run's report: header
`Mode: **model**`, **model verdicts accepted: 4/6** — #101 (bug, P0),
#102 (feature, P3), #103 (question, P3) and #105 (bug, P1) came from the
model, each marked `source: "model"`. The other two issues fell back
honestly and say so in the run log: #104 failed at the provider
(`ProviderError: INVALID_ARGUMENT`, "Tool transcript invariant failed")
and #106's model verdict was rejected by the validation gate (it used the
label `chore`, which is not in the closed label vocabulary). The earlier
deterministic-stub example (`examples/expected-output-stub.md`,
`Mode: **stub**`) is untouched. The first live attempt the same day
returned 0/6 because the model drifted off the contract (bare objects
without `issue_number`, natural-language priorities like `high`/`critical`,
a `{"issues": [...]}` wrapper); the prompt was tightened to restate the
exact category/priority strings and require `issue_number`, and the parser
now accepts the `issues` wrapper and a bare single-issue verdict — with
every field still validated, and no synonym mapping. See
`BUILDING-BLOCKS-TESTED.md` §6. Before this run, the full OpenMinion path
had only been executed against the SDK's non-model `echo` provider
(OpenMinion 0.1.13, installed from PyPI): the agent turn completed, the
echo output failed validation on all six issues, every verdict was
stub-replaced and logged, and — after a labeling bug that this run exposed
was fixed — the report labeled itself `stub` with "model verdicts
accepted: 0/6" in its run log. See `BUILDING-BLOCKS-TESTED.md` §3. To
reproduce the live run:

```bash
# fw-proxy listening on 127.0.0.1:8791 (it attaches the credential)
PATCHMINION_PROXY_KEY=proxy .venv/bin/python -m patchminion examples/issues.json \
    --mode auto --out examples/expected-output-model.md \
    --json-out examples/expected-output-model.json
```

`--mode auto` tries the model and, if the provider is unavailable, falls
back for the whole batch *and says so in the report and the run log*.
`--mode model` makes a provider failure a hard error. `--mode stub` never
calls the model (CI / offline smoke tests).

## How the OpenMinion SDK workflow works here

PatchMinion uses the documented 0.1.x Python facade only
(`openminion/__init__` exports; see `API_COMPATIBILITY.md` in the SDK repo):

1. **Tools** — two read-only functions are decorated with `@tool`
   (`patchminion/agent.py`): `get_issue(issue_number)` serves one issue
   from the batch, `label_vocabulary()` serves the closed label list.
2. **Agent** — `Agent(instructions=..., tools=[...], session_id=...,
   config_path=...)` is used as a context manager. One `agent.run(prompt)`
   turn triages the whole batch; `result.text` carries the reply and
   `result.session_id` is written into the run log.
3. **Contract** — the instructions require a single JSON object:
   `{"triage": [{issue_number, category, labels, priority, summary,
   first_response}, ...]}`.
4. **Validation gate** — `patchminion/parsing.py` extracts the first
   balanced JSON object from the reply and validates every field against
   the closed vocabularies in `patchminion/models.py`. A verdict that
   fails is replaced by the deterministic stub *for that issue only*, and
   the rejection reason is recorded in the run log.
5. **Report** — `patchminion/report.py` renders a Markdown report plus a
   JSON run log. Both carry a SHA-256 fingerprint of the input fixture, so
   any run can be tied back to exactly the input it triaged.

```
fixture JSON ──> load_issues ──> Agent.run (tools: get_issue,
                                    label_vocabulary)
                                      │ result.text
                                      ▼
                              parse + validate ── invalid ──> stub (logged)
                                      │ valid
                                      ▼
                    Markdown report + JSON run log (fixture fingerprint)
```

## Setup

```bash
python3.11+ -m venv .venv && source .venv/bin/activate
pip install -e .            # installs openminion 0.1.x from PyPI
# for a real model run, configure one provider:
openminion config init      # or set the provider's API-key env var
```

## Run the working example

```bash
# offline / no key — deterministic stub, labeled as such:
python -m patchminion examples/issues.json --mode stub \
    --out examples/expected-output-stub.md

# real model-backed run (needs a configured provider):
python -m patchminion examples/issues.json \
    --out out/report.md --json-out out/runlog.json
```

Input format (`examples/issues.json`): a JSON list of
`{"number", "title", "body", "labels"}` — exactly what the GitHub issues
API returns, trimmed. In **stub mode**, the example produces (abridged;
full file: `examples/expected-output-stub.md`):

| Issue | Category | Priority | Labels | Source |
|---|---|---|---|---|
| #101 App crashes on startup after upgrading to 2.4.0 | bug | P1 | bug, crash, regression | fallback |
| #102 Add support for exporting reports as PDF | feature | P2 | enhancement, ui | fallback |
| #103 How do I configure the webhook retry policy? | question | P2 | question, api, good-first-issue | fallback |
| #104 Typo in the README quickstart and outdated API example | docs | P3 | documentation, api, good-first-issue | fallback |
| #105 Dashboard is very slow when a project has more than 10k tasks | bug | P2 | bug, performance, ui | fallback |
| #106 Bump lodash to 4.17.21 and refresh CI cache keys | chore | P1 | enhancement, security | fallback |

Fixture fingerprint: `a0e871411cd5`.

## Tests

The non-model logic (JSON extraction, verdict validation, keyword stub,
fixture loading, report rendering) is unit-tested with no SDK install and
no credentials:

```bash
python -m pytest tests/ -q
# 18 passed
```

## Repository layout

| Path | What |
|---|---|
| `patchminion/models.py` | Issue/Triage types, closed vocabularies, fixture loading |
| `patchminion/parsing.py` | Defensive JSON extraction + verdict validation |
| `patchminion/fallback.py` | Deterministic keyword stub (clearly labeled) |
| `patchminion/agent.py` | The only module importing `openminion` (`Agent`, `@tool`) |
| `patchminion/report.py` | Markdown report + JSON run log, fixture fingerprint |
| `patchminion/cli.py` | CLI (`auto` / `model` / `stub` modes) |
| `examples/issues.json` | Working example input (6 issues) |
| `examples/expected-output-stub.md` | Real output of the example in stub mode |
| `tests/test_patchminion.py` | 18 tests for the non-model logic |
| `BUILDING-BLOCKS-TESTED.md` | SDK blocks exercised, with commands + evidence |
| `WHAT-WE-LEARNED.md` | Actionable feedback from building on OpenMinion 0.1 |
| `DEMO-SCRIPT.md` | Shot list + narration for the 1–5 min demo video |

## What remains for submission

1. Run one live model pass (provider key) and record the demo video per
   `DEMO-SCRIPT.md`, with the `Mode: **model**` header on screen.
2. Publish this directory as a public GitHub repo.
3. Open the PR to the organizer's Hackathon #5 repo once its URL is
   published, linking the repo, the notes, and the video.
