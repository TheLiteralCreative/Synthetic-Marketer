# FORWARD_PLAN — Synthetic-Marketer (a.k.a. SignalRipper)

**Last updated:** 2026-05-13
**Current version:** GUI v0.1.0 (B5) · `discover.py` v0.3.0 · `qa.py` v0.1.0 · Active/Legacy bin layout · QA-after-PDFs fix · Cloudflare Tunnel deployed at `signalripper.literalcreative.com` (auth gate pending) · tool rebranding to **SignalRipper** in progress

> **Naming note.** The repo is still named `Synthetic-Marketer`; the tool is being renamed to **SignalRipper** (signal extraction from a website's noise). Public URL is `signalripper.literalcreative.com`. In-app strings (GUI title, README header, `/api/ping` name field, etc.) still say "Synthetic-Marketer" — rebrand pass scheduled, see priority list below.

---

## Where we are

Synthetic-Marketer is a **local-first marketing audit pipeline** that produces shareable, client-ready deliverables for any website in 10–15 minutes. The full pipeline runs end-to-end via either:

- **GUI**: `python3 start.py` → browser at `localhost:8000`
- **CLI**: `python3 -m backend.audit_runner <url> <bin>`

The pipeline is in **production** for personal use. Three real audits have been validated (Capstone, Flexent, Hewitt + a smoke test on example.com). All five existing project bins pass QA cleanly.

**Repo:** https://github.com/TheLiteralCreative/Synthetic-Marketer (private)

---

## Recent activity (last session — 2026-05-13)

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

In rough priority order. The tool works as-is locally and via the tunnel (when started); none of these are blocking that.

1. **[TOGETHER] PRIORITY — Cloudflare Access auth gate.** Stand up Google OAuth + email allowlist in front of `signalripper.literalcreative.com` before the tunnel goes back up. Operator handles the Cloudflare Zero Trust dashboard (Access → Applications → Add an application → Self-hosted → application domain `signalripper.literalcreative.com` → add Google as identity provider → policy "Allow" with email rule listing operator + invited collaborators). Claude assists with policy structure and verifies the auth flow works end-to-end. Until this ships, do NOT run `cloudflared tunnel run signalripper` in a way that leaves the URL up — the tool is currently unauthenticated.

2. **[CLAUDE]** Run a real audit through `https://signalripper.literalcreative.com` once auth is in place, and confirm SSE phase events stream live (not buffered). The named-tunnel SSE path is documented as working in practice but the smoke test is non-skippable per `docs/REMOTE-HOSTING.md` §3 step 7. If buffering shows up, the three escalating fixes are listed in that section.

3. **[CLAUDE]** Write `~/Library/LaunchAgents/com.signalripper.cloudflared.plist` so the tunnel auto-starts on login and survives sleep/wake. Document the `launchctl load`/`unload` commands. Reference `cloudflared service install` as an alternative path (it generates the plist automatically) — pick the cleaner approach during implementation.

4. **[CLAUDE]** Build the `/publish-tool` skill from this session's deployment experience. Inputs: subdomain + local port. Pre-checks: parent domain on Cloudflare, `cloudflared` installed + logged in. Auto-runs: `tunnel create`, `tunnel route dns`, append ingress rule to `~/.cloudflared/config.yml`, generate launchd plist, smoke-test the URL. Manual gate: Cloudflare Access app creation (or automate via Cloudflare API if an API token is configured). Goal: next tool deployment (e.g. ScriptRipper migration to this pattern, or ON-SET Compiler when ready) becomes a one-liner.

5. **[CLAUDE]** Rebrand pass: `Synthetic-Marketer` → `SignalRipper` in user-visible strings. Audit list of files: `frontend/src/` (page titles, header text, browser tab title), `backend/__init__.py` (`__version__` is fine but check for name string), `backend/routes.py` `/api/ping` returns `name="Synthetic-Marketer"` — change to `SignalRipper`. README.md header. Don't rename the repo or Python package (keeps git history sane); only customer-facing strings.

6. **[YOU]** Email deliverability cleanup on `literalcreative.com` (carried over from the DNS migration recon — known but not fixed tonight):
   - Edit SPF TXT record in Cloudflare DNS from `v=spf1 include:_spf.wpcloud.com ~all` to `v=spf1 include:_spf.google.com ~all`. Outbound mail from `@literalcreative.com` via Gmail is currently failing SPF.
   - Set up DKIM signing in Google Workspace admin (Apps → Google Workspace → Gmail → Authenticate email). Generate the key, paste the resulting `google._domainkey` TXT record into Cloudflare DNS. ~10 min.

7. **[TOGETHER]** Apply the same DNS migration + tunnel pattern to ScriptRipper (per operator's plan to consolidate). Migrate `scriptripper.com` from current registrar/DNS to Cloudflare DNS. Then either (a) deploy ScriptRipper as a Cloudflare-tunneled subdomain like SignalRipper, OR (b) keep current Render deployment and just consolidate DNS — depends on whether ScriptRipper has the same constraints (long jobs, headless Chrome, etc.) that disqualified Render for SignalRipper. Worth the `/publish-tool` skill being built first so this becomes a one-liner.

8. **[TOGETHER]** Decide consolidation pattern: the operator wants `scriptripper.com` and `signalripper.com` (and presumably future tool domains) to "point to the literalcreative page" eventually. Several patterns to choose from — single hub site with links to subdomains, 301 redirects from old apex domains to LC subpages, full DNS merger. Discuss and pick a pattern when traffic justifies the move off the operator's local Mac (per `docs/REMOTE-HOSTING.md` §6 trigger conditions).

9. **[YOU]** Run one or more real audits and observe quality in production (carried over). The fixed pipeline now surfaces testimonials/blockquotes, runs Active/Legacy correctly, and produces clean QA reports. If new accuracy gaps surface, those become the next round of fixes.

10. **[YOU]** Get a free Google PageSpeed Insights API key, set in Settings (carried over). 5 minutes at console.cloud.google.com.

11. **[YOU]** Read through `docs/METHODOLOGY.md` and direct edits before external use (carried over). Particularly Q22 pricing language, section 3 tone, closing workflow paragraph.

12. **[TOGETHER]** Backlog triage — see `tools/BACKLOG.md` for deferred ideas. Item #9 (remote hosting) is now substantially done; remaining highest-impact:
   - **Brand voice profile deliverable** (BACKLOG #3) — generates a `BRAND-VOICE.md` per audit
   - **Re-audit / delta tracking** (BACKLOG #4) — `tools/delta.py` compares two bins of the same brand

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
