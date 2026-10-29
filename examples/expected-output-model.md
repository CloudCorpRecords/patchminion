# PatchMinion triage report

- Mode: **model** (model-backed)
- Issues: 6 · fixture fingerprint: `a0e871411cd5`
- Verdicts from the model: 4/6

| Issue | Category | Priority | Labels | Source |
|---|---|---|---|---|
| #101 App crashes on startup after upgrading to 2.4.0 | bug | P0 | bug, crash, regression | model |
| #102 Add support for exporting reports as PDF | feature | P3 | enhancement, ui | model |
| #103 How do I configure the webhook retry policy? | question | P3 | question, documentation, api | model |
| #104 Typo in the README quickstart and outdated API example | docs | P3 | documentation, api, good-first-issue | fallback |
| #105 Dashboard is very slow when a project has more than 10k tasks | bug | P1 | bug, performance, ui | model |
| #106 Bump lodash to 4.17.21 and refresh CI cache keys | chore | P1 | enhancement, security | fallback |

## Details

### Issue #101 — App crashes on startup after upgrading to 2.4.0

- **Summary:** App crashes immediately on launch for all Windows users after upgrading to 2.4.0, due to a NullPointerException in SessionStore.load. This is a regression from 2.3.1 that completely blocks startup on Windows.
- **Suggested first response:** Thanks for the report — confirmed as a P0 regression since it prevents all Windows users from launching 2.4.0. We're prioritizing a fix for the NullPointerException in SessionStore.load (last working in 2.3.1). As a workaround, please roll back to 2.3.1. We'll post updates here as we investigate; a stack-trace-linked commit or repro details are welcome.

### Issue #102 — Add support for exporting reports as PDF

- **Summary:** Feature request to add PDF export for the monthly report in the dashboard, via an export button next to the existing CSV export button.
- **Suggested first response:** Thanks for the suggestion! Exporting the monthly report as a PDF sounds like a useful addition. We've triaged this as a feature request and will consider adding a PDF export button alongside the CSV one in a future release. As an interim workaround, you can use your browser's print-to-PDF option on the report page.

### Issue #103 — How do I configure the webhook retry policy?

- **Summary:** User asks where to configure webhook retry frequency and whether a custom backoff can be set; the API docs mention that retries occur but do not document any settings for them. No defect reported — this is a how-to question that also exposes a documentation gap.
- **Suggested first response:** Thanks for the question! Right now the retry interval/backoff for failed webhooks is not exposed as a configurable setting, and our docs only note that retries happen without describing the timing. Could you share your use case (e.g., how quickly you'd want retries and what backoff curve you need)? We'll flag the docs gap so the webhook retry behavior is documented explicitly, and if custom backoff isn't currently supported we'll convert this into a feature request and follow up here.

### Issue #104 — Typo in the README quickstart and outdated API example

- **Summary:** The README quickstart has a typo in the install command and the API example still uses the removed v1 endpoint
- **Suggested first response:** Thanks for the report! Triage (automated stub): this looks like a docs (P3). A maintainer will confirm the suggested labels: documentation, api, good-first-issue.

### Issue #105 — Dashboard is very slow when a project has more than 10k tasks

- **Summary:** Dashboard takes 20+ seconds to render and spikes browser CPU when a project exceeds 10k tasks, likely because the task list is rendered without pagination.
- **Suggested first response:** Thanks for the detailed report — 20+ second render times at 10k+ tasks is a serious performance problem. We've triaged this as a performance bug; our initial hypothesis matches yours, that the unpaginated task list is rendering all rows at once. To help us confirm while we profile the dashboard rendering path, could you share your browser/OS version and whether smaller projects (~5k tasks) still feel responsive?

### Issue #106 — Bump lodash to 4.17.21 and refresh CI cache keys

- **Summary:** Chore: bump the lodash dependency to 4
- **Suggested first response:** Thanks for the report! Triage (automated stub): this looks like a chore (P1). A maintainer will confirm the suggested labels: enhancement, security.

## Run log

- openminion sessions: patchminion-triage-101, patchminion-triage-102, patchminion-triage-103, patchminion-triage-105, patchminion-triage-106
- issue #104: model run failed (ProviderError: INVALID_ARGUMENT: The configured model provider failed before it could return a decision (Tool transcript invariant failed). Please retry or switch models.); deterministic stub used for this issue
- issue #106: model verdict rejected (labels outside vocabulary: ['chore']); deterministic stub used for this issue
- model verdicts accepted: 4/6
