"""PatchMinion — a reproducible GitHub-issue triage agent built on OpenMinion 0.1.

The package splits cleanly into three layers:

* Pure logic (no I/O, fully unit-tested): ``models``, ``parsing``, ``fallback``.
* The OpenMinion glue: ``agent`` (an ``openminion.Agent`` with ``@tool``
  functions; this is the only module that imports ``openminion``).
* The CLI: ``cli`` (also runnable as ``python -m patchminion``).
"""

__version__ = "0.1.0"
