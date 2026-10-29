# Building blocks tested — PatchMinion

What we actually exercised while building PatchMinion, and the evidence.
SDK under test: **OpenMinion 0.1.x** (`openminion` on PyPI; source:
github.com/openminion/openminion). Environment: Python 3.12.3, Linux.

## 1. Python facade imports and agent/tool API — VERIFIED FROM SOURCE + DOCS

Source files read in the SDK repo before writing any code:

- `README.md` — Quick Start embedding example:
  `from openminion import Agent, ProviderError, tool`, `@tool` on a typed
  function, `with Agent(instructions=..., tools=[...], session_id=...) as
  agent: result = agent.run(...)`, `result.text`, `result.session_id`.
- `examples/starter/quickstart.py` — the canonical minimal program:
  `Agent(tools=[hello_tool])`, `agent.run(prompt)`, `print(result.text)`,
  `from openminion import __version__`.
- README "Runtime Surfaces" — the supported root-package exports:
  `APIRuntime`, `Agent`, `AgentOutputValidationError`, `AgentRunResult`,
  `Handoff`, `MemoryBundle`, `OpenMinionConfig`, `ProviderError`,
  `TurnTimeoutError`, `subagent`, `tool`, `__version__`, with
  `API_COMPATIBILITY.md` named as the contract for the 0.1.x surface.

PatchMinion's `patchminion/agent.py` deliberately uses only this facade:
`Agent`, `tool`, `ProviderError`, context-manager use, one `run()` turn,
two tools. No deep `openminion.*` internals are imported anywhere.

## 2. Provider configuration model — VERIFIED FROM README

- `openminion config init` / `openminion setup --list-providers [--json]`
  enumerate providers; setup asks for provider, model, and credential, and
  OpenMinion selects the API adapter automatically (MiniMax stays the
  provider even on an OpenAI-compatible API).
- `openminion config init --provider echo` + `openminion run "hello"` is
  the credential-free tour; the README states plainly that demo mode
  "does not call a model" and readiness labels it `demo`, not `ready`.
  PatchMinion therefore never uses the echo provider as demo evidence —
  see the live-run status in the README and `WHAT-WE-LEARNED.md`.

## 3. Installed SDK — EXECUTED against the real package (0.1.13)

`pip install openminion pytest` into a venv (Python 3.12.3), then
introspection of the installed package confirmed every facade assumption
from §1 against the real signatures:

- `openminion.__version__` → `0.1.13`; CLI `openminion --version` → `0.1.13`
- `Agent.__init__` keyword parameters include `instructions`, `tools`,
  `session_id`, `config_path`, `agent_id`, `model`, `runtime`, `handoffs`
  — and `output_type` (see `WHAT-WE-LEARNED.md` #3)
- `tool(func=None, *, name, description, min_scope, dangerous, idempotent,
  tags, capabilities)` — bare `@tool` usage is valid
- `AgentRunResult` fields: `output, text, raw, run_id, run_state,
  session_id, id, metadata, stats` — `.text` and `.session_id` as used

CLI smoke test (isolated `OPENMINION_HOME`/`OPENMINION_DATA_ROOT`):

```bash
openminion config init --provider echo
# Initialized config at .../.openminion/agents.json
openminion run "hello"
# openminion: hello (thinking=minimal)   <- echo plumbing, NOT a model
```

Then PatchMinion itself, in `--mode auto`, against that echo config: the
`Agent` turn completed (session `patchminion-triage`), the echo reply
contained no JSON, all six verdicts were rejected and stub-replaced, and
the run log recorded each rejection plus `model verdicts accepted: 0/6`.
This run caught a real bug — the report header initially claimed
`Mode: model` despite 0/6 model verdicts; mode labeling is now derived
from the verdicts (`patchminion/cli.py: effective_mode`, covered by a
unit test) and the same run now labels itself `stub`. The scratch echo
config was deleted afterward.

## 4. PatchMinion's own pipeline — EXECUTED, with output

Commands run in this workspace:

```bash
python3 -m pytest tests/ -q
# 18 passed in 0.11s   (also: 18 passed under the venv interpreter)

python3 -m patchminion examples/issues.json --mode stub \
    --out examples/expected-output-stub.md \
    --json-out examples/expected-output-stub.json
# Report header: Mode: **stub** (deterministic stub — NOT a model run)
# Issues: 6 · fixture fingerprint: a0e871411cd5 · model verdicts: 0/6
```

The stub table (all six verdicts manually reviewed for sanity):

| Issue | Category | Priority | Labels |
|---|---|---|---|
| #101 startup crash after upgrade | bug | P1 | bug, crash, regression |
| #102 PDF export request | feature | P2 | enhancement, ui |
| #103 webhook retry question | question | P2 | question, api, good-first-issue |
| #104 README typo / stale example | docs | P3 | documentation, api, good-first-issue |
| #105 slow dashboard at 10k tasks | bug | P2 | bug, performance, ui |
| #106 lodash bump + CI cache | chore | P1 | enhancement, security |

## 5. Blocks NOT exercised (and why)

- **Live hosted-model `Agent.run`** — exercised 2026-10-28, see §6 below.
  (Before that date no hosted provider credential existed in this build
  environment, so only an echo-backed turn had been executed end-to-end
  (§3). The failure paths are first-class: `--mode auto` catches
  provider/config errors and labels the fallback.)
- **`APIRuntime.submit_turn` / streaming / `subagent` / `Handoff`** — real
  blocks in the facade, but unnecessary for a one-turn batch tool; using
  them would be résumé-padding, not engineering.
- **Memory, MCP, A2A, daemon (`openminiond`), HTTP API** — out of scope for
  this entry; the triage batch is stateless and one-shot by design.
- **CLI surface beyond docs** (`openminion tools list`, `doctor`, agent
  inspect) — read in the README's command list, not run in this
  environment.

## 6. Live hosted-model run — EXECUTED 2026-10-28

Provider: Fireworks `accounts/fireworks/models/glm-5p3-flash` through the
pack's local `fw-proxy` (provider slot `openai` →
`http://127.0.0.1:8791/inference/v1`; the proxy attaches the real
credential, so no key is committed here). Command:

```bash
PATCHMINION_PROXY_KEY=proxy .venv/bin/python -m patchminion examples/issues.json \
    --mode auto --out examples/expected-output-model.md \
    --json-out examples/expected-output-model.json
# Report header: Mode: **model** (model-backed)
# Issues: 6 · fixture fingerprint: a0e871411cd5 · model verdicts: 4/6
```

Per-issue outcome (shipped as `examples/expected-output-model.md/.json`):

| Issue | Source | Verdict |
|---|---|---|
| #101 startup crash | model | bug, P0, bug/crash/regression |
| #102 PDF export request | model | feature, P3, enhancement/ui |
| #103 webhook retry question | model | question, P3, question/documentation/api |
| #104 README typo | fallback | provider error, see below |
| #105 slow dashboard | model | bug, P1, bug/performance/ui |
| #106 lodash bump | fallback | gate rejection, see below |

The two fallbacks are honest, not hidden: #104 failed at the provider on
every live attempt (`ProviderError: INVALID_ARGUMENT`, "Tool transcript
invariant failed" — an SDK/provider-side failure, not a parse issue);
#106's model verdict was rejected by the validation gate because it used
the label `chore`, which is not in the closed label vocabulary
(`patchminion/models.py: LABEL_VOCABULARY`). The gate was NOT weakened to
admit either one.

What the live runs changed in the code (prompt/parsing, gate intact):
- The first live attempt the same day returned 0/6: the model drifted off
  the contract — bare objects without `issue_number`, natural-language
  priorities (`critical`/`high`/`medium`/`low` instead of P0–P3), a
  `{"issues": [...]}` wrapper, and one prose refusal with no JSON.
- `patchminion/agent.py`: the instructions and the per-issue prompt now
  restate the exact category/priority strings, forbid synonyms, and
  require `issue_number`.
- `patchminion/parsing.py`: accepts the `issues` wrapper as an alias for
  `triage` (entries still matched by `issue_number`), and attributes a
  bare verdict object with no `issue_number` to the requested issue (the
  turn asked for exactly one issue; a named-but-different issue is still
  rejected). Every field is still validated; natural-language priorities
  and out-of-vocabulary labels are still rejected, covered by tests.
- `patchminion/parsing.py`: the category-label insert no longer duplicates
  a label the model already gave (feature → `enhancement` was doubled on
  #102 in the intermediate run).
- Test suite after these changes: 23 passed (was 18; 5 new tests cover the
  parser tolerances and the still-strict rejections).

The deterministic stub example (`examples/expected-output-stub.md`,
`Mode: **stub**`) is untouched by the live runs.
