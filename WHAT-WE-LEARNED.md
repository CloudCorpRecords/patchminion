# What we learned — building PatchMinion on OpenMinion 0.1

Actionable feedback from one real build. Everything below was hit during
this project, not collected from docs summaries.

## What worked well

1. **The Python facade is genuinely small.** `Agent`, `tool`,
   `ProviderError`, `AgentRunResult` — the whole integration fit in one
   120-line module (`patchminion/agent.py`), and the README's embedding
   example plus `examples/starter/quickstart.py` were sufficient to write
   it without reading runtime internals. That is the right shape for an
   SDK people are supposed to build hackathon entries on.
2. **The echo provider's honesty labeling is exemplary.** The README says
   outright that demo mode "does not call a model" and that readiness
   reports `demo`, not `ready`. We copied that pattern into PatchMinion
   itself (every verdict and report is labeled `model` vs `fallback`).
   More SDKs should ship a lie detector for their own demos.

## Friction and suggestions

3. **Structured output exists but is undiscoverable from the docs.**
   We needed one JSON object per batch, so we prompt-engineered the format
   and wrote a defensive parser (balanced-brace extraction + schema and
   vocabulary validation, ~90 lines) to survive prose-wrapped or truncated
   replies. Only afterwards, introspecting the installed 0.1.13 package,
   did we find `output_type` in `Agent.__init__`'s signature — the README
   quick-start and `examples/starter/quickstart.py` never mention it, and
   neither did the facade export list (`AgentOutputValidationError` was
   the only hint). We kept our tested parser rather than adopt a contract
   we could not find documented anywhere we read (what type it expects,
   how mismatches surface). **Suggestion:** one quick-start example using
   `output_type=` would save every embedder the archaeology — the feature
   is already built.
4. **Config resolution differs by surface in ways that surprise —
   proven firsthand.** Per the README, bare CLI runs save config to
   `~/.openminion/agents.json`, while direct `openminion mcp ...` commands
   default to `./.openminion/agents.json`, matching the Python SDK's
   project-scoped default. This stopped being theoretical during our own
   testing: a scratch echo config created for a CLI smoke test in the
   project directory was silently picked up by PatchMinion's next
   `--mode auto` run via that project-scoped default, and the agent ran
   against the echo provider. (Our validation gate is what surfaced it:
   the run log showed six "no JSON object in model reply" rejections.)
   PatchMinion exposes an explicit `--config` flag mapping to the
   documented `config_path=` parameter, and we deleted the scratch config.
   **Suggestion:** one resolution diagram in the docs (per surface:
   flag > env > project file > home file), plus a startup log line naming
   the config file actually loaded, would save every embedder the same
   surprise.
5. **Tool state has no documented home.** Our tools need the current issue
   batch, so the batch lives in a module-level dict the tools read. It
   works, but a documented pattern — per-`Agent` tool state, or tools as
   bound methods/closures shown in an example — would remove the global
   and the guesswork. (`@tool` on plain functions is clean; state is the
   missing chapter.)
6. **Keyword stubs lie fluently; validation is not optional.** Our first
   stub pass matched substrings, so "quickstart" suggested the `ui` label
   ("ui" inside "quickstart") and a config question scored P1 because its
   body contained "cannot". Both were caught only because we unit-tested
   verdicts against hand-labeled expectations. This is a PatchMinion bug,
   not an OpenMinion one — but it is why PatchMinion validates *model*
   output with the same rigor: fluent text, whether from an LLM or a
   keyword list, needs a deterministic gate before it touches a tracker.
7. **Docs are strong on operating the runtime, thinner on embedding it.**
   The operator story (CLI, Focus, rooms, permissions) is documented in
   depth; the embedder story is essentially one quick-start example. An
   "Embedding cookbook" — multi-tool agent, structured output, custom
   config path, error taxonomy (`ProviderError` vs `TurnTimeoutError` vs
   `AgentOutputValidationError`) — would shorten the path for the exact
   audience a hackathon brings.
