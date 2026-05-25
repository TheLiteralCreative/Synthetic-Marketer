# Phase 1 Brief — SignalRipper Tunnel Deployment

Brief for Claude Code working in the `Synthetic-Marketer/` folder. Phase 1 finishes the
Cloudflare Tunnel deployment so SignalRipper is live, gated, and shareable.

**Read first:** `HOSTING-ROADMAP.md` (why tunnel, not Render), `CLOUDFLARE-ACCESS-SETUP.md`,
`DEDICATED-HOST-SETUP.md`, and `FORWARD_PLAN.md` (the canonical task list).

---

## Context

SignalRipper deploys via Cloudflare Tunnel, not Render — its audit is a 10–15 minute
synchronous job that Render's web services cannot host without an async refactor. The
tunnel (`signalripper.literalcreative.com`) is already created and smoke-tested. Phase 1
splits in two:

- **Phase 1a (now):** auth gate + verification → SignalRipper goes live.
- **Phase 1b (later):** move the tunnel to a dedicated always-on machine.

The Cloudflare Access auth gate is the **operator's** task (Cloudflare dashboard, no
code) — tracked in `CLOUDFLARE-ACCESS-SETUP.md`. The tasks below are Claude Code's part.

---

## Task A — Rebrand pass (do first; independent of everything else)

Rename `Synthetic-Marketer` → `SignalRipper` in **user-visible strings only**. Per
`FORWARD_PLAN.md` priority #5:

- `frontend/src/` — page titles, header text, browser tab `<title>`.
- `backend/routes.py` — the `/api/ping` response currently returns
  `name="Synthetic-Marketer"`; change to `SignalRipper`.
- `backend/__init__.py` — check for a name string (the `__version__` is fine to leave).
- `README.md` — the header.

**Do not** rename the git repository or the Python package — that keeps git history and
imports intact. Customer-facing strings only.

## Task B — Verification audit (after the operator finishes the auth gate)

This task is **blocked** until the operator confirms the Cloudflare Access gate is live
(Step 5 of `CLOUDFLARE-ACCESS-SETUP.md`). Then:

1. Run one real audit end-to-end through `https://signalripper.literalcreative.com`.
2. Confirm the In-Progress view streams phase/cost/log events **live**, not in a single
   buffered dump at the end. This SSE check is non-skippable — `REMOTE-HOSTING.md` §3
   step 7.
3. If events are buffered, apply the three escalating fixes in `REMOTE-HOSTING.md` §3, in
   order (explicit `Cache-Control: no-cache, no-transform` on the SSE response → disable
   Cloudflare auto-minify/rocket-loader for the subdomain → confirm HTTP/1.1 chunked
   encoding).

## Task C — Explicitly DEFER these

- **launchd persistence service** (`FORWARD_PLAN.md` #3) — do **not** build it yet. It
  belongs on the dedicated machine, not the laptop. It is a Phase 1b task; see
  `DEDICATED-HOST-SETUP.md` §3 step 6.
- **`/publish-tool` skill** (`FORWARD_PLAN.md` #4) — defer until after the dedicated-host
  cutover, so the skill captures the complete, proven pattern rather than a half of it.

## Task D — Housekeeping

- Update `FORWARD_PLAN.md` to reflect the Phase 1a / 1b split and the hosting decision;
  point it at `HOSTING-ROADMAP.md` as the canonical hosting reference.
- Close the session per the project's `/session-close` convention.

---

## Out of scope for this brief (operator routes separately)

The canonical `MEDIA_RIPPERS_PROGRAM_PLAN.md` lives in the `literalcreative-strategy`
repo. Its Phase 1 still says "deploy SignalRipper to Render" and needs updating per
`HOSTING-ROADMAP.md` §1 (the runtime-shape rule). That edit is not part of this brief
because it is a different repository — handle it when Claude Code is pointed at the
strategy repo, or via the parent folder.

## Workflow notes

- Point VSCode / Claude Code at the `Synthetic-Marketer/` folder for this work.
- Cowork edits files; the operator commits and pushes from the terminal.
- Tasks A and D can be done now. Task B waits on the operator's auth-gate step.
