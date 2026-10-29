"""PatchMinion CLI.

Modes:
* default (``--mode auto``): try a real OpenMinion model run; if the
  provider is not configured / fails, fall back to the deterministic stub
  for the whole batch and say so in the report header and the run log.
* ``--mode model``: require the model; a provider failure is an error.
* ``--mode stub``: never call the model (CI, smoke tests, offline demo of
  the pipeline only — the output is labeled as a stub everywhere).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import fallback
from .models import Triage, load_issues
from .report import render_json_log, render_markdown


def effective_mode(verdicts: list[Triage]) -> str:
    """The honest mode label: "model" only if at least one verdict in the
    report genuinely came from the model. A completed agent turn whose
    output failed validation everywhere (or that ran against OpenMinion's
    non-model echo provider) must not label the report model-backed."""
    return "model" if any(v.source == "model" for v in verdicts) else "stub"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="patchminion",
        description="Reproducible GitHub-issue triage agent (OpenMinion 0.1).",
    )
    parser.add_argument("fixture", help="JSON file with the issues to triage")
    parser.add_argument("--mode", choices=("auto", "model", "stub"),
                        default="auto")
    parser.add_argument("--config", default=None,
                        help="path to an OpenMinion agents.json config "
                             "(default: OpenMinion's own resolution)")
    parser.add_argument("--out", default=None,
                        help="also write the Markdown report to this path")
    parser.add_argument("--json-out", default=None,
                        help="also write the JSON run log to this path")
    args = parser.parse_args(argv)

    issues = load_issues(args.fixture)
    log: list[str] = []
    verdicts = None
    mode_used = "stub"

    if args.mode in ("auto", "model"):
        try:
            from .agent import ProviderError, run_model_triage

            verdicts, model_log = run_model_triage(
                issues, config_path=args.config
            )
            log.extend(model_log)
            mode_used = effective_mode(verdicts)
            if mode_used == "stub":
                log.append(
                    "agent turn completed but produced no valid model "
                    "verdicts; report labeled stub"
                )
        except Exception as exc:  # ProviderError or config/import problems
            name = exc.__class__.__name__
            if args.mode == "model":
                print(f"error: model run failed ({name}: {exc})",
                      file=sys.stderr)
                return 2
            log.append(
                f"model run unavailable ({name}: {exc}); whole batch "
                "triaged with the deterministic stub"
            )

    if verdicts is None:
        verdicts = [fallback.classify_issue(i) for i in issues]
        mode_used = "stub"

    markdown = render_markdown(issues, verdicts, mode=mode_used, log=log)
    print(markdown)
    if args.out:
        Path(args.out).write_text(markdown, encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(
            render_json_log(issues, verdicts, mode=mode_used, log=log),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
