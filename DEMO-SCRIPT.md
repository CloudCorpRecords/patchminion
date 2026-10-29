# PatchMinion demo video script (target: 3–4 minutes, hard cap 5)

Recording notes: 1080p terminal capture, font ≥16pt. Record the **live model
run** (Mode: model in the report header). If the recording environment has
no provider key, record the stub run but keep the on-screen honesty label
visible and say so in the narration — never present a stub run as a model
run.

## Shot list

| # | Time | On screen | Narration |
|---|---|---|---|
| 1 | 0:00–0:20 | Title card + README top | "This is PatchMinion, a GitHub issue triage agent built on the OpenMinion 0.1 SDK for Cortensor Hackathon #5. It was built by AI agents directed by a human, and it triages issues the same way: a model proposes, deterministic code disposes." |
| 2 | 0:20–0:50 | `examples/issues.json` in an editor | "Here is the input: six real-shaped issues — a startup crash, a feature request, a how-to question, a docs fix, a performance report, and a dependency bump. Same fixture, same fingerprint, every run." |
| 3 | 0:50–1:10 | `patchminion/agent.py` — the `@tool` functions and `INSTRUCTIONS` | "The agent gets exactly two tools: read an issue, and read the closed label vocabulary. It must answer with one JSON object — category, labels, priority, a one-line summary, and a draft first response." |
| 4 | 1:10–2:10 | Terminal: `python -m patchminion examples/issues.json --out out/report.md` (live run) | "One OpenMinion agent turn triages the whole batch. Watch the header: Mode: model — that line matters, because PatchMinion labels its own output. If the model returns a label outside the vocabulary, that verdict is rejected, replaced by a deterministic stub, and the replacement is written into the run log. Nothing fails silently." |
| 5 | 2:10–2:50 | `out/report.md` — scroll the table, open two Details entries | "Six verdicts: the crash is a P1 bug with regression and needs-repro labels, the lodash bump is a chore that carries the security label it deserves, and every issue has a summary plus a ready-to-post first response a maintainer can accept or edit." |
| 6 | 2:50–3:20 | Terminal: `python -m patchminion examples/issues.json --mode stub` then `python -m pytest -q` | "No API key? The same pipeline runs offline on a deterministic keyword stub, and the report says so in its header — that's the smoke-test path, not the demo path. The parsing, validation, and triage logic is covered by unit tests that need no credentials." |
| 7 | 3:20–3:50 | `BUILDING-BLOCKS-TESTED.md` + `WHAT-WE-LEARNED.md` | "We documented every OpenMinion building block we exercised, and what we learned — including the sharp edges, like the echo provider being a plumbing demo rather than a model run. Links to reproduce everything are in the README." |

## Reproducibility checklist for the recording

- [ ] `openminion --version` shown or noted in the description (SDK 0.1.x).
- [ ] Report header visibly shows `Mode: **model**` for the main run.
- [ ] Fixture fingerprint in the report matches `examples/issues.json`.
- [ ] The stub run is shown only as the labeled offline path.
