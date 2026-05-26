# FORWARD_PLAN — Synthetic-Marketer (a.k.a. SignalRipper)

**Last updated:** 2026-05-25
**Current version:** GUI v0.1.0 (B5) · `discover.py` v0.3.0 · `qa.py` v0.1.0 · Active/Legacy bin layout · QA-after-PDFs fix · **Phase 1b complete — SignalRipper live and unattended on LC-NODE-01 via launchd persistence**, behind Cloudflare Access at `https://signalripper.literalcreative.com` · tool rebranding to **SignalRipper** in progress

> **Naming note.** The repo is still named `Synthetic-Marketer`; the tool is renamed to **SignalRipper** (signal extraction from a website's noise). Public URL is `signalripper.literalcreative.com`. In-app strings (GUI title, README header, `/api/ping` name field, etc.) still say "Synthetic-Marketer" — rebrand pass scheduled, see priority list below.

---

## Where we are

Synthetic-Marketer / SignalRipper is a **marketing audit pipeline** that produces shareable, client-ready deliverables for any website in 10–15 minutes. It runs end-to-end via either:

- **GUI**: browser at `https://signalripper.literalcreative.com` (production) or `http://localhost:8000` (local dev)
- **CLI**: `python3 -m backend.audit_runner <url> <bin>`

As of 2026-05-25, the tool runs **unattended on LC-NODE-01** (the Late-2015 27" iMac) via two `launchd` user agents — SignalRipper and the Cloudflare tunnel both start on boot, restart on crash, and need no Terminal windows. Access is gated by Cloudflare Access (Google OAuth + email allowlist) until the planned Kit-auth retrofit (priority #3 below) replaces gateway-level auth with app-level identity.

**Repo:** https://github.com/TheLiteralCreative/Synthetic-Marketer (private)

---

## Recent activity (last session — 2026-05-25)

Phase 1b finished. Full completion-state handoff in `docs/PHASE-1B-STATE.md`; full session record in `docs/session-log/2026-05-25.md`.

Notable shipped:

- ✓ **launchd persistence on LC-NODE-01.** Two user LaunchAgents (`com.literalcreative.signalripper` + `com.literalcreative.cloudflared`) committed to `deploy/launchd/` and deployed to `~/Library/LaunchAgents/` on the iMac. `RunAtLoad` + `KeepAlive` + `ThrottleInterval` 10. SignalRipper runs `start.py --no-open` under the venv python; `cloudflared` runs with explicit `--config`. Process output redirected to `~/srv/logs/`. **Verified via cold reboot:** both services auto-started with fresh low PIDs (415, 418) and `https://signalripper.literalcreative.com` served the GUI with no manual intervention. This is the proof that the unattended-host goal is met, not just configured.
- ✓ **Real audit run end-to-end through the public URL, SSE streaming verified live.** Operator initiated an audit through `https://signalripper.literalcreative.com` during the launchd-managed run; In-Progress view updated gradually phase by phase, not as an end-of-run dump. Non-skippable SSE check from `REMOTE-HOSTING.md` §3 step 7 — **passed**.
- ✓ **Laptop tunnel decommissioned.** Confirmed no `cloudflared` process and no `launchd` service for it on the laptop. NODE_01 is the sole host answering the `signalripper` tunnel.
- ✓ **Anthropic API key + per-machine output folder set on NODE_01.** Output folder `/Users/literalcreative/srv/apps/signalripper`. 16 existing audit bins (Active + Legacy) mirrored from the laptop to NODE_01; the GUI's bin list picks them up automatically (`backend/active_audits.py`'s `list_bins()` is a pure filesystem glob — no import step needed).
- ✓ **`docs/PHASE-1B-STATE.md` rewritten** as a completion-state handoff with operating reference and updated breadcrumbs.
- ✓ **`.claude/commands/session-open.md` + `session-close.md`** copied from ScriptRipper into this repo, closing a discipline gap (the `docs/session-log/` and `FORWARD_PLAN.md` infrastructure was already here; only the slash-command files were missing).

Strategic decisions:

- **Kit-auth chosen as the first concrete Ripper Kit module** (rather than copy-pasting ScriptRipper's auth into SignalRipper). Extract `auth.py` + `core/security.py` + `User` model into a reusable Kit module; both ScriptRipper and SignalRipper consume it; future Rippers inherit it. Solves the open user-approval / record-retention / remote-approval questions cleanly via an `is_approved` flag.
- **Shared auth does not require shared hosting.** ScriptRipper stays on Render (paying customers + Stripe + SLA preclude operator-Mac dependency per `HOSTING-ROADMAP.md` §6); SignalRipper stays on NODE_01; both consume the same Kit-auth module. JWT-based identity makes one-login-every-Ripper trivially possible across hosts. v1 = per-Ripper User tables; v2 (3+ Rippers, several users) = shared identity DB.
- **Cloudflare Access on `signalripper.literalcreative.com` is the temporary v1 gate.** Comes off when Kit-auth lands on SignalRipper.

Known issue:

- **Universal Clipboard, iMac → laptop, is unreliable.** Copy works laptop → iMac but not the reverse; `killall pboard`, Handoff re-toggle, and a full reboot did not fix it. Apple Notes (iCloud sync) used as a working bridge during this session. Open for fresh investigation — possibly Continuity-cache reset (iCloud sign-out / sign-in) or an OS-version mismatch (Monterey iMac vs. current-macOS laptop).

## Recent activity (prior session — 2026-05-13)

Big session. Three feature/fix shipments + the entire DNS-and-tunnel deployment that the prior session had filed as backlog #9 PRIORITY. See `docs/session-log/2026-05-13.md` for full detail.

Notable shipped:

- ✓ **Active-Audits / Legacy-Audits convention** — new module `backend/active_audits.py` plus `backend/routes.py` patches at four call sites. New audits land in `Active-Audits/`; when a fresh audit runs against a brand that already has an Active folder, the existing folder is auto-demoted to `Legacy-Audits/<bin>_<N>` (case-insensitive brand match, iteration count derived from existing Legacy folders + 1). GUI's audit list shows Active only; Legacy is archive-only. 13 pre-existing root-level bins migrated into `Active-Audits/`; 2 pre-existing un-suffixed Legacy folders normalized to `_1` suffix. `tools/AUDIT-PROCESS.md` updated to document the convention. Verified end-to-end with smoke tests. Gitignore updated.
- ✓ **QA timing fix (false-positive PDF warnings eliminated)** — `backend/audit_runner.py` now re-runs QA silently after Phase 8 and overwrites `_QA-REPORT.md`. Root cause: Phase 6 QA ran before Phases 7-8 generated the dashboard PDF and 7 per-markdown PDFs, so every audit's report false-flagged 8 missing PDFs. Fix is a 5-line append after `_phase8_pdfs`. Re-ran QA across all 13 Active bins to clean stale reports — 11 came up "ready to ship," 1 surfaced a real phone-number inconsistency (FLEXENTFREIGHT — accepted), 1 surfaced a real cross-audit-reference rule match (ZAPATA-ESTATES — accepted as false positive on the rule).
- ✓ **literalcreative.com DNS migrated WordPress → Cloudflare** — full external recon → adding zone to Cloudflare → record verification → Cloudflare set all 10 records to DNS-only (avoiding double-proxy through Manus's Cloudflare) → nameservers updated at GoDaddy from `ns1/2/3.wordpress.com` to `clayton.ns.cloudflare.com` + `elisa.ns.cloudflare.com` → activation completed within ~1.5hr → brand site verified loading post-flip via Cloudflare-resolver and Google-resolver dig + curl HTTP 200. Two known email-deliverability concerns NOT fixed tonight (logged for later): (a) SPF record still authorizes only WordPress, should authorize Google Workspace (`v=spf1 include:_spf.google.com ~all`); (b) no DKIM signing detected (Google Workspace admin task, ~10 min).
- ✓ **Cloudflare Tunnel deployed** — `cloudflared` v2026.5.0 installed via brew → `cloudflared tunnel login` (cert at `~/.cloudflared/cert.pem`) → tunnel `signalripper` created (UUID `2e97776b-dacf-403c-97a7-91380488ff3e`) → DNS routed (CNAME `signalripper.literalcreative.com` → tunnel) → `~/.cloudflared/config.yml` written with single ingress rule `signalripper.literalcreative.com → http://localhost:8000` → smoke-test confirmed: GUI loads in browser at `https://signalripper.literalcreative.com` with valid Cloudflare-issued SSL cert. Tunnel stopped end of session (Ctrl+C) since auth gate not yet configured — see priority #1 below.
- ✓ **Tool rebrand decided: Synthetic-Marketer → SignalRipper** — naming-consistent with ScriptRipper (Ripper family of LiteralCreative tools). "Signal" captures the actual mental model — extracting strategic signal from a website's noise. URL `signalripper.literalcreative.com` already provisioned. In-app string rebrand pass deferred to next session.

## Recent activity (prior session — 2026-05-09)

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

In rough priority order. The deploy workflow (#1) is the immediate unblocker for any forward code change, including the operator's planned delivery-report feature work on SignalRipper.

1. **[CLAUDE]** **Deploy workflow** — laptop → GitHub → NODE_01. Runbook + a one-command deploy script on NODE_01 (`~/srv/bin/deploy-signalripper.sh`) that pulls from GitHub, restarts the SignalRipper `launchd` service (`launchctl unload`/`load -w`), and prints clear pass/fail. Document the upgrade path to automated pull (cron poll or GitHub webhook) for later. Designed as universal practice — same shape works for ScriptRipper, ON-SET Compiler, every future Ripper.

2. **[CLAUDE]** **Scalable health-check + monitoring v1 for NODE_01.** Scheduled check that confirms SignalRipper stays reachable, with a single combined report channel ready to grow as Rippers multiply. **One decision needed first:** how the monitor gets past the Cloudflare Access gate — either a Cloudflare Access service token, or checking the tunnel's health via Cloudflare's API. The wrinkle dissolves once Kit-auth (#3–#4) replaces Cloudflare Access on SignalRipper.

3. **[CLAUDE]** **Extract Kit-auth module from ScriptRipper.** Pull `app/api/auth.py` + `app/core/security.py` + `User` model out as the first reusable Ripper Kit module. SQLAlchemy-based so Postgres (ScriptRipper) and SQLite (NODE_01) work interchangeably. Add the `is_approved` flag pattern for gated registration. This is the centerpiece of the Ripper Kit effort.

4. **[CLAUDE]** **Retrofit SignalRipper with Kit-auth.** Wire Kit-auth into SignalRipper: SQLite User table on NODE_01, login screen + OAuth callback in the frontend, JWT-protected API endpoints, admin tap-to-approve flow. Register a new Google OAuth client for `signalripper.literalcreative.com` (separate from ScriptRipper's). Remove the Cloudflare Access app from the subdomain once app-auth is live and verified.

5. **[YOU/TOGETHER]** **Update `literalcreative.com`** to showcase active Rippers, with the Kit-auth login as the entry point for each tool. Scope depends on the current site structure; partially gated on #4 landing.

6. **[CLAUDE]** Rebrand pass: `Synthetic-Marketer` → `SignalRipper` in user-visible strings. Audit list: `frontend/src/` (page titles, header text, browser tab title), `backend/__init__.py` (name string), `backend/routes.py` `/api/ping` returns `name="Synthetic-Marketer"` — change to `SignalRipper`. README.md header. Don't rename the repo or Python package (keeps git history sane); customer-facing strings only.

7. **[YOU]** Email deliverability cleanup on `literalcreative.com` (carried over):
   - Edit SPF TXT record in Cloudflare DNS from `v=spf1 include:_spf.wpcloud.com ~all` to `v=spf1 include:_spf.google.com ~all`. Outbound mail from `@literalcreative.com` via Gmail is currently failing SPF.
   - Set up DKIM signing in Google Workspace admin (Apps → Google Workspace → Gmail → Authenticate email). ~10 min.

8. **[TOGETHER]** ScriptRipper consolidation — *reframed 2026-05-25.* Original plan was to migrate ScriptRipper to a Cloudflare-tunneled subdomain on NODE_01 (priority #7 in the prior list). Architectural call as of this session: keep ScriptRipper on Render (paying customers + Stripe + SLA preclude operator-Mac dependency per `HOSTING-ROADMAP.md` §6) and instead consolidate the *user experience* via shared Kit-auth (priorities #3–#4 above). The domain-consolidation question for `scriptripper.com` / `signalripper.com` / future Ripper domains remains open — single hub page with subdomain links, 301 redirects to LC subpages, etc. — discuss when traffic justifies it.

9. **[YOU]** Run more real audits in production and observe quality. The fixed pipeline now runs Active/Legacy correctly, surfaces testimonials/blockquotes, and produces clean QA reports. New accuracy gaps become the next round of fixes.

10. **[YOU]** Get a free Google PageSpeed Insights API key, set in Settings (carried over). 5 min at `console.cloud.google.com`.

11. **[YOU]** Read through `docs/METHODOLOGY.md` and direct edits before external use. Particularly Q22 pricing language, section 3 tone, closing workflow paragraph.

12. **[TOGETHER]** Backlog triage — see `tools/BACKLOG.md`. Item #9 (remote hosting) is now fully done. Highest-impact remaining:
   - Brand voice profile deliverable (BACKLOG #3)
   - Re-audit / delta tracking (BACKLOG #4)

13. **[YOU]** Carried-over breadcrumbs from `PHASE-1B-STATE.md`:
   - Tonight's `/session-close` handles committing the new `deploy/launchd/` plists, `docs/LC-NODE-01_Infrastructure-Strategy.md`, `docs/PHASE-1B-STATE.md`, and `.claude/commands/` files.
   - Rotate the two exposed credentials flagged earlier in the program (Stripe test key + GitHub PAT).
   - Update `MEDIA_RIPPERS_PROGRAM_PLAN.md` per `HOSTING-ROADMAP.md` §1.
   - Mark `DEDICATED-HOST-SETUP.md` steps 6–8 complete in that doc.
   - Hand `PHASE-1-BRIEF.md` to Claude Code pointed at the `Synthetic-Marketer` folder.

---

## Backlog

See [`tools/BACKLOG.md`](../tools/BACKLOG.md) for the deferred-features list (8 items, with effort estimates and decision log).

---

## Locked decisions (architectural)

- **No Claude Agent SDK dep** — pivoted to direct `anthropic` SDK. Reason: agent SDK isn't on PyPI under the name we expected; direct API gives more control + sidesteps the Claude Code permissions layer entirely.
- **Local-first GUI** — FastAPI + React served as a single deployment unit. Now hosted unattended on LC-NODE-01.
- **In-memory job queue** — by design for a single-user tool. Job state dies with the server. Bins on disk are the persistent record.
- **No cost-ceiling abort mid-audit** — explicitly rejected. Manual cancel button + correct cost meter + post-Phase-1 estimate is the right shape; mid-audit abort would waste partial work and force re-runs.
- **Hard rule: self-contained audits** — no cross-audit references in any deliverable. `tools/qa.py` enforces this with regex pattern matching. Sibling-bin brand-name leakage check uses generic-token stop-list to avoid false positives on smoke-test bins.
- **Two hand-written user LaunchAgents over `cloudflared service install`** *(2026-05-25)* — one mental model, one set of `launchctl` commands, consistent management across both services. The official `service install` would have created a system-level daemon for the tunnel while SignalRipper needs its own user agent — different locations, different commands, two ways to think about it. The marginal automation isn't worth the inconsistency.
- **Kit-auth as the first concrete Ripper Kit module** *(2026-05-25)* — extract from ScriptRipper rather than copy-paste into SignalRipper. The first time a pattern needs a second consumer is the right moment to extract it. Gives the Ripper Kit a high-value module to start with rather than a generic skeleton.
- **SQLite for SignalRipper's user table** *(2026-05-25)* — matches NODE_01's local-disk model; no external DB dependency. SQLAlchemy keeps the schema interchangeable with ScriptRipper's Postgres.
- **Cloudflare Access on `signalripper.literalcreative.com` is temporary** *(2026-05-25)* — it exists because we needed a gate fast and didn't want to write auth code. Comes off when Kit-auth lands on SignalRipper.

---

## Operating notes

- **SignalRipper on NODE_01 runs via two user LaunchAgents** — `com.literalcreative.signalripper` and `com.literalcreative.cloudflared` in `~/Library/LaunchAgents/`. Version-controlled at `deploy/launchd/`.
- **Check status:** `launchctl list | grep literalcreative` on the iMac. Real PID + `0` exit = healthy.
- **Watch live activity:** `tail -f ~/srv/logs/signalripper.out.log` — the launchd-era replacement for watching a Terminal window. Process output is redirected to log files because launchd-managed processes have no controlling Terminal.
- **Restart a service:** `kill` alone will NOT stop it — `KeepAlive` respawns immediately. Use `launchctl unload <plist>` then `launchctl load -w <plist>`.
- **Deploy updated code (manual, today):** `git pull` on NODE_01, then `unload` + `load` the SignalRipper agent. (Will be a single command once priority #1 lands.)
- **Cost per audit:** $0.25–$1.50 with Haiku for typical small/medium sites; $1–$4 Sonnet; $3–$15 Opus. Pre-flight estimate after Phase 1 sets expectations per-site.
- **API key location on NODE_01:** `~/srv/apps/signalripper/data/settings.json` (gitignored). Set via Settings tab in GUI or shell env var `ANTHROPIC_API_KEY`.
- **Project bins are gitignored.** Per-audit deliverables stay local on whichever machine ran them.
- **Output folder configurable** via Settings — NODE_01's is `/Users/literalcreative/srv/apps/signalripper`.

---

## Session log archive

All historical session logs in [`docs/session-log/`](session-log/).
