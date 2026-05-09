# FORWARD_PLAN — Synthetic-Marketer

**Last updated:** 2026-05-09
**Current version:** GUI v0.1.0 (B5 polish complete) · `discover.py` v0.3.0 · `qa.py` v0.1.0 · client-facing methodology brief shipped · remote-hosting plan documented

---

## Where we are

Synthetic-Marketer is a **local-first marketing audit pipeline** that produces shareable, client-ready deliverables for any website in 10–15 minutes. The full pipeline runs end-to-end via either:

- **GUI**: `python3 start.py` → browser at `localhost:8000`
- **CLI**: `python3 -m backend.audit_runner <url> <bin>`

The pipeline is in **production** for personal use. Three real audits have been validated (Capstone, Flexent, Hewitt + a smoke test on example.com). All five existing project bins pass QA cleanly.

**Repo:** https://github.com/TheLiteralCreative/Synthetic-Marketer (private)

---

## Recent activity (last session — 2026-05-09)

Two non-engineering deliverables shipped — a client-facing methodology brief for sales/authority use, and a documented remote-hosting plan filed as a priority backlog item. See `docs/session-log/2026-05-09.md` for full detail.

Notable shipped:
- ✓ **Client-facing methodology brief** (`docs/METHODOLOGY.md`, 2026-05-09) — durable "What / How / Why" reference doc + 25 anticipated FAQ answers. Grounds authority in the actual pipeline mechanics (six weighted categories, eight-phase flow, ten QA checks, ~30 mechanical evidence points, named precedent stack). Designed for use as a sales support asset and client onboarding brief. Not regenerated per-audit.
- ✓ **Remote-hosting plan** (`docs/REMOTE-HOSTING.md`, 2026-05-09) — canonical reference for moving the tool from local-only to invited-collaborator access at strict zero cost. Recommends Cloudflare Tunnel + Cloudflare Access (Google OAuth + email allowlist, 50-user cap, no code changes). Documents Tailscale alternative, six rejected paths with reasons, and the trigger conditions for a future cloud refactor.
- ✓ **BACKLOG #9** — added "Remote hosting / collaborator access" with `[PRIORITY]` flag, referencing the standalone plan.

## Recent activity (prior session — 2026-05-08)

GUI built end-to-end across five build phases (B1–B5) plus four mid-flight bug fixes uncovered by real-use shakedown. See `docs/session-log/2026-05-08.md` for full detail.

Notable shipped:
- ✓ **GUI** (`backend/` + `frontend/`) — FastAPI + React, single-command launch, browser-driven audits, real-time SSE progress, sortable past-audit browser, one-click PDF opens, OS-level "Open folder" + "Re-render PDFs" actions
- ✓ **Cost-meter heads-up** — Phase 1 emits estimated remaining cost based on digest size + selected model (calibrated to two real audits)
- ✓ **Discovery content-excerpts** (`tools/discover.py` v0.3.0) — testimonials, blockquotes, hero copy now surfaced in `_DIGEST.md`. Closes a systemic blindness where pure-metadata digests led subagents to false "no testimonials" claims
- ✓ **Cross-platform Chrome detection** in `md_to_pdf.py` (macOS / Windows / Linux / Edge fallback)
- ✓ **README + AUDIT-PROCESS.md + BACKLOG.md** all current

---

## Active priorities — next session pickup

In rough priority order. **None of these are blocking** — the tool works as-is and the user can simply run audits.

1. **[TOGETHER] PRIORITY — Remote hosting deployment.** Deploy Cloudflare Tunnel + Cloudflare Access per the plan in `docs/REMOTE-HOSTING.md`. Operator handles DNS / Cloudflare Zero Trust dashboard setup; Claude writes the launchd plist for `cloudflared` persistence and helps smoke-test SSE through the named tunnel. ~2 hours of work split across one operator + one Claude session, plus DNS propagation. Engage when the operator is ready to share access with the first collaborator.

2. **[YOU]** Run one or more real audits and observe quality in production. The fixed pipeline should now surface testimonials and other body content correctly. If new accuracy gaps surface, those become the next round of fixes.

3. **[CLAUDE]** If/when you flag a content-extraction gap from a real audit (e.g., pricing language missed, value-prop signal missed, service descriptions), apply the same surgical pattern as the testimonial fix — add a new extraction strategy to `tools/discover.py` and surface it in `_DIGEST.md`.

4. **[YOU]** Consider getting a free Google PageSpeed Insights API key and setting `PAGESPEED_API_KEY=…` in `data/settings.json` (or `.env`). Anonymous PSI rate-limits aggressively. With a key, audits get reliable Core Web Vitals data in every run. ~5 minutes at console.cloud.google.com.

5. **[YOU]** Read through `docs/METHODOLOGY.md` and direct any edits before it gets used as a sales asset. Particularly worth a sanity pass: pricing language in Q22 ("low-four-figures range"), tone calibration in section 3 ("why pay for this"), and the closing workflow description.

6. **[TOGETHER]** Backlog item triage — see `tools/BACKLOG.md` for 9 deferred ideas. After remote hosting (now #9, flagged priority), the two highest-impact remaining:
   - **Brand voice profile deliverable** (BACKLOG #3) — generates a `BRAND-VOICE.md` per audit; valuable when audits feed downstream content production
   - **Re-audit / delta tracking** (BACKLOG #4) — `tools/delta.py` to compare two bins of the same brand; valuable for retainer/recurring-audit workflows

---

## Backlog

See [`tools/BACKLOG.md`](../tools/BACKLOG.md) for the deferred-features list (8 items, with effort estimates and decision log).

---

## Locked decisions (architectural)

- **No Claude Agent SDK dep** — pivoted to direct `anthropic` SDK. Reason: agent SDK isn't on PyPI under the name we expected; direct API gives more control + sidesteps the Claude Code permissions layer entirely.
- **Local-first GUI** — FastAPI + React served as a single deployment unit on `localhost:8000`. No cloud deployment. API key stays on the operator's machine.
- **In-memory job queue** — by design for a single-user tool. Job state dies with the server. Bins on disk are the persistent record.
- **No cost-ceiling abort mid-audit** — explicitly rejected. Manual cancel button + correct cost meter + post-Phase-1 estimate is the right shape; mid-audit abort would waste partial work and force re-runs.
- **Hard rule: self-contained audits** — no cross-audit references in any deliverable. `tools/qa.py` enforces this with regex pattern matching. Sibling-bin brand-name leakage check uses generic-token stop-list to avoid false positives on smoke-test bins.

---

## Operating notes

- **Cost per audit:** $0.25–$1.50 with Haiku for typical small/medium sites; $1–$4 Sonnet; $3–$15 Opus. Pre-flight estimate after Phase 1 sets expectations per-site.
- **API key location:** `data/settings.json` (gitignored). Set via Settings tab in GUI or shell env var `ANTHROPIC_API_KEY`.
- **Project bins are gitignored.** Per-audit deliverables stay local. The repo ships only the tool.
- **Output folder configurable** via Settings — default is project root.

---

## Session log archive

All historical session logs in [`docs/session-log/`](session-log/).
