# Remote Hosting Plan — Synthetic-Marketer

Reference document for the future deployment of Synthetic-Marketer beyond local-only operation. Compiled as the canonical source for the engineering decision; revisit when the work is scheduled.

**Status:** planning only. Tool currently runs local-only at `localhost:8000` via `python3 start.py`. No cloud infrastructure exists.

---

## 1. Decision criteria

Two constraints fix the scope of this decision:

| Criterion | Choice |
|---|---|
| **Who can use the hosted version** | Operator + 2–4 invited collaborators. No public signup. Gated access. |
| **Cost posture** | Strict zero-cost. Free tiers only. Accept reasonable tradeoffs (cold starts, manual operator presence) to stay at $0/mo baseline. |

These constraints disqualify several common paths and concentrate the answer on minimum-infrastructure exposure of the existing local tool.

---

## 2. Recommended path — Cloudflare Tunnel + Cloudflare Access

The tool stays exactly where it is — running on the operator's Mac via `python3 start.py`. Cloudflare Tunnel exposes `localhost:8000` at a real public URL (e.g. `https://synthetic.scriptripper.com`). Cloudflare Access puts Google OAuth and an email allowlist in front of it.

### What this configuration produces

| Property | Value |
|---|---|
| Monthly cost | $0 |
| Code changes required | None |
| Auth | Google OAuth + email allowlist (Cloudflare Access free tier covers up to 50 users) |
| Public URL | Any subdomain of a Cloudflare-managed domain |
| Headless Chrome | Stays on the Mac, no Docker, no slim-container restyling |
| SSE progress streams | Work on **named** Cloudflare tunnels (smoke test required — quick tunnels buffer SSE) |
| Long-running jobs (10–15 min) | No platform timeout — the Mac runs the job, Cloudflare proxies. Cloudflare connection limit is 8 hours. |
| Persistent storage | Project bins remain on local disk where they already are |
| Existing cost meter, QA, PDF rendering | Unchanged |

### The one real constraint

The operator's Mac must be online for collaborators to run audits. For a 3-person tool, this is the right tradeoff. Mitigations:

- `caffeinate -i` keeps the Mac awake while collaborators are using the tool.
- macOS "Wake for network access" can let the Mac come out of sleep on incoming requests.
- A long-running `cloudflared` instance via `launchd` ensures the tunnel persists across login sessions.

If the Mac-must-be-online constraint ever becomes binding (operator wants to ship audits while traveling without bringing the Mac, or the access model expands), the upgrade path is documented in section 5.

---

## 3. Implementation outline

| Step | What | Owner | Time |
|---|---|---|---|
| 1 | Move `scriptripper.com` (or another owned domain) to Cloudflare DNS | Operator | ~5 min config + ~30 min DNS propagation |
| 2 | Install `cloudflared` on the Mac (`brew install cloudflared`) | Operator | 1 min |
| 3 | `cloudflared tunnel login` + `cloudflared tunnel create synthetic-marketer` | Operator | 5 min |
| 4 | DNS route: `cloudflared tunnel route dns synthetic-marketer synthetic.<domain>` | Operator | 1 min |
| 5 | Write `~/.cloudflared/config.yml` with the `localhost:8000` ingress rule | Claude / Operator | 5 min |
| 6 | Smoke-test: `cloudflared tunnel run synthetic-marketer` + verify the public URL serves the GUI | Operator | 5 min |
| 7 | **SSE verification** — run a real audit through the public URL, confirm the In-Progress view streams phase events without buffering | Operator | 15–20 min (one full audit) |
| 8 | Convert to launchd service so the tunnel persists across reboots and login sessions | Claude | 15 min — write the `.plist`, document the load command |
| 9 | Cloudflare Zero Trust dashboard: create Access application targeting the subdomain; add Google OAuth identity provider; configure email allowlist policy with the 2–4 invited addresses | Operator | 15 min |
| 10 | Hand collaborators the URL and have each complete the OAuth flow once | Operator + collaborators | 5 min per person |

**Total:** ~2 hours of work split across one operator session and one Claude session, plus DNS propagation wait. Smoke test is the real gating step.

### Smoke-test gotcha — SSE

Cloudflare's quick tunnels buffer Server-Sent Events. The Synthetic-Marketer In-Progress view depends on SSE for live phase / cost / log streaming, so a buffered tunnel would break the user-visible progress experience even though the audit itself would still complete in the background.

**Named tunnels stream SSE correctly in practice**, but documented edge cases exist for SSE-over-GET. The smoke test in step 7 is non-skippable: run a real audit through the tunnel and confirm phase events arrive in real time, not in a single dump at the end.

If buffering shows up:
- First fix: ensure no `Cache-Control` defaults in front of the SSE endpoint (FastAPI / sse-starlette already sets `Cache-Control: no-cache`, but Cloudflare's defaults can override — explicitly set `Cache-Control: no-cache, no-transform` on the SSE response).
- Second fix: disable Cloudflare auto-minify and rocket-loader for the subdomain (Speed → Optimization).
- Third fix: confirm the response is sent with HTTP/1.1 chunked encoding from FastAPI side (sse-starlette does this by default).

---

## 4. Alternative path — Tailscale

Lighter-weight than Cloudflare Tunnel, but requires every collaborator to install the Tailscale app on each device.

| Property | Value |
|---|---|
| Monthly cost | $0 (free Personal plan: 6 users / unlimited devices) |
| Auth | Implicit — "you're on the Tailnet, you're in" |
| URL | `http://<mac-machine-name>.<tailnet>.ts.net:8000` |
| SSE | Raw TCP — no buffering concerns |
| Setup time | ~30 minutes |

**When to choose Tailscale over Cloudflare Tunnel:** when the collaborators are technical, you want zero cloud proxy in the path, and you're OK with each collaborator installing a VPN client.

**When to choose Cloudflare Tunnel over Tailscale:** when collaborators are non-technical, you want a normal `https://` URL they can open in any browser without installing software, and you want OAuth with an audit log.

For a small marketing-tool collaborator group, Cloudflare Tunnel is the better default.

---

## 5. Rejected paths

Documenting these explicitly so the decision doesn't get re-litigated when this work is picked up.

| Path | Why rejected |
|---|---|
| **Render free Web Service** | (a) Free instances sleep after 15 min idle with ~1 min cold start. (b) HTTP request timeout disqualifies a 10–15 min pipeline at the edge — Render's supported pattern for long jobs is paid background workers. (c) 512 MB RAM on free instances will OOM under headless Chrome. (d) 0.1 CPU is too thin for the parallel subagent phase. |
| **Render Starter (paid, $7/mo)** | Plausible technically, but violates the strict-zero-cost constraint. Also requires (i) replacing headless Chrome with WeasyPrint and restyling PDF templates to avoid Flexbox/Grid (Chrome on Render is fragile and memory-hungry), (ii) migrating the in-memory job queue to Upstash Redis, (iii) writing project bins to Cloudflare R2 instead of local disk. Significant refactor for no functional gain over Cloudflare Tunnel at this scale. |
| **Fly.io free tier** | Effectively eliminated for new accounts in late 2024. New orgs get a 2-VM-hour or 7-day trial, then pay-as-you-go with credit card required. Stopped machines still bill rootfs storage. Not zero-cost in 2026 unless an org was grandfathered in. |
| **Vercel / Netlify functions** | Long-running jobs are not the supported pattern (free-tier function timeouts of 10–30 seconds, paid tier maxes around 15 min). SSE on edge functions is fragile. Audit pipeline runtime alone disqualifies this path. |
| **Cloudflare Workers / Pages Functions** | 10ms CPU limit per request on the free tier. Not a candidate for a 10–15 min pipeline. |
| **Self-hosted on a $5 VPS (DigitalOcean / Linode / Hetzner)** | Violates strict-zero-cost. Otherwise viable; revisit only if the access model expands beyond a small invited group and the Mac-must-be-online constraint becomes binding. |

---

## 6. Trigger conditions to revisit

Move from "Cloudflare Tunnel exposes the local Mac" to a real cloud deployment when **any** of these become true:

1. The collaborator group grows beyond ~10 users, or includes anyone who needs to run audits on a schedule the operator can't reliably honor.
2. The operator wants to run audits programmatically (cron, webhook, API integration) without the Mac being awake.
3. Audits become a paid product offering with paying clients — at that point, uptime SLAs and operator-Mac dependency become unacceptable.
4. The pipeline gains a feature that requires shared compute (e.g. delta tracking against a shared historical bin store accessible to multiple operators).

Until one of those triggers fires, the Cloudflare Tunnel approach is the correct architecture — not a stopgap.

### What the cloud-refactor path looks like (when triggered)

For reference, the work required to lift Synthetic-Marketer into a fully cloud-hosted form:

1. **Replace headless Chrome with WeasyPrint** in `tools/md_to_pdf.py`. Restyle PDF templates to use CSS Paged Media features WeasyPrint handles well (running headers/footers, page numbers, margin boxes) and avoid Flexbox/Grid layouts that WeasyPrint handles poorly. Container size drops from ~1.5–2 GB (Chromium) to ~200–400 MB (WeasyPrint).
2. **Migrate in-memory job queue to Upstash Redis.** Job state survives restarts; multiple worker processes become possible. Free tier: 500K commands/month, 256 MB max DB, ~1,100 typical audits/month before exhaustion.
3. **Write bins to Cloudflare R2 instead of local disk.** Free tier: 10 GB storage, 1M writes/mo, 10M reads/mo, $0 egress. Modify `audit_runner.py` to upload bin contents to R2 on completion; modify the GUI bin-browser endpoints to read from R2.
4. **Containerize and deploy.** Choice depends on cost-floor tolerance at that point — Render Starter ($7/mo), Fly.io paid (usage-priced), or a $5 VPS.
5. **Persist Anthropic / PSI API keys as secrets** in the host's secret manager, not in `data/settings.json`.
6. **Settings UI changes** — the GUI's Settings tab currently writes to `data/settings.json`; for hosted use, settings either become per-user (each collaborator brings their own API key) or stay operator-controlled (single shared key, environment-variable-loaded).

All of this is documented here so it doesn't have to be re-derived when the trigger fires.

---

## 7. References

Source data behind this plan, captured May 2026:

- Cloudflare Tunnel free tier — 1,000 tunnels / 500 Access apps per account; named tunnels are the production path; Cloudflare One connection cap of 8 hours per long-lived connection.
- Cloudflare Access free plan — 50 users, full ZTNA features, 24-hour log retention, 3-location cap, full identity-gated app sharing.
- Cloudflare R2 free tier — 10 GB storage, 1M Class A ops, 10M Class B ops, $0 egress.
- Upstash Redis free tier — 500K commands/month, 256 MB max DB, up to 10 free DBs, HTTP API (not persistent connection).
- Tailscale free Personal plan (April 2026 pricing v4) — 6 users, unlimited devices, 50 tagged resources, 1,000 ephemeral resource-minutes/month. The legacy 100-device cap is gone.
- Render free Web Service — 750 instance hours/month, 15-min idle sleep, ~1-min cold start, 512 MB RAM / 0.1 CPU on free instances.
- Fly.io — free tier effectively removed for new accounts in late 2024. Trial → pay-as-you-go.
- WeasyPrint vs headless Chrome — WeasyPrint is Python-native, no Chromium, ~10× lower RAM per render, strong on CSS Paged Media, weaker on Flexbox/Grid, no JavaScript execution. Slow on large docs (52-page test ~100s) but fine for typical Synthetic-Marketer report sizes.

---

*This document is the canonical reference for the remote-hosting decision. When the work is scheduled, follow the implementation outline in section 3 and update the BACKLOG entry with the actual deployment date and the URL the tool ends up on.*
