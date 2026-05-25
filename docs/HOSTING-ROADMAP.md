# SignalRipper — Hosting Roadmap

Companion to `REMOTE-HOSTING.md`. That document made the original local-only → tunnel
decision. This one picks up after it: it records a re-assessment of how SignalRipper's
hosting fits the wider Media Rippers program, defines the three hosting tiers, and
documents — in real detail — the background-worker refactor a full cloud move would
require, so that decision is costed and ready rather than re-derived under pressure.

**Status:** Tier 1 in progress (auth gate). Tier 2 is the planned durable home. Tier 3 is
documented-but-not-scheduled.

---

## 1. Re-assessment — where this leaves the plan

The Media Rippers program plan briefly carried a blanket rule: *Rippers deploy to
Render.* That was a reasonable simplification when the goal was to stop scattered, ad hoc
infrastructure choices. But it collided with a fact in SignalRipper's own engineering
record: **a SignalRipper audit is a single synchronous 10–15 minute operation with a
human watching it.** Render's web services structurally cannot host that without
refactoring the tool into an async job-plus-worker architecture (see §4).

The fix is not to abandon consolidation — it is to make the consolidation rule correct.

> **The rule: hosting follows runtime shape.**

A tool's runtime shape — *how* it runs, not *what* it does — determines its host:

| Runtime shape | Description | Correct host |
|---|---|---|
| **Interactive / long-synchronous** | A person triggers a long job and waits, watching live progress | Tunnel from an always-on machine |
| **Unattended / async / scheduled** | Runs on a schedule by itself, nobody waiting | Render web service |
| **Static site / thin API** | No long jobs at all | Cloudflare Pages |

SignalRipper is the first shape — interactive, long, watched. **ScriptRipper is the
second** — its Daily Rip is cron-triggered, runs via `BackgroundTasks`, and emails the
result with nobody waiting on a request. The two tools have *opposite* runtime shapes, so
they correctly get different hosts. That is not inconsistency; forcing them onto one host
would be — it would mis-host one of them. (Tunneling ScriptRipper would tie an unattended
daily tool to a machine being awake every morning at cron time, re-breaking the exact
thing Render gets right.)

**This keeps the Kit universal.** The Media Rippers Kit stays a single universal
framework — spine, auth/credit model, R2 storage, docs convention, scaffolding process.
Hosting becomes one *parameter* the scaffolding process sets by asking a single question:
*interactive-and-watched, or unattended?* The Kit carries both deployment playbooks (the
tunnel guide and the Render guide) and a one-question router between them. Universal
framework, universal decision procedure — not a uniform output.

**Ripple to the phases:** Phase 1 (SignalRipper) becomes "finish the tunnel," not "deploy
to Render." Phase 2 (ScriptRipper) is unchanged — Render is still correct. Phase 3 (the
Kit) gains the one-question hosting router instead of the hardcoded "Rippers → Render"
rule. The canonical `MEDIA_RIPPERS_PROGRAM_PLAN.md` should be updated to match.

---

## 2. The three tiers

### Tier 1 — Laptop tunnel (today)

Cloudflare Tunnel exposes `localhost:8000` on your Mac at
`signalripper.literalcreative.com`; Cloudflare Access gates it. Already ~80% built per
`REMOTE-HOSTING.md` — the tunnel is created and smoke-tested; only the auth gate remains
(`CLOUDFLARE-ACCESS-SETUP.md`). Cost: $0. Limitation: your laptop must be awake and online
for anyone to use the tool.

### Tier 2 — Dedicated-machine tunnel (the durable home)

The same tunnel, but running from a low-power machine that is always on, instead of your
laptop. This removes Tier 1's only real weakness — `REMOTE-HOSTING.md`'s one knock on the
tunnel path was "the operator's Mac must be online," and a dedicated box eliminates it
outright. No code changes, no refactor, still $0/month for a machine you own and
repurpose. Setup in `DEDICATED-HOST-SETUP.md`.

This is SignalRipper's intended durable home. For an interactive tool used by a small
invited group, Tier 2 is not a stepping stone — it is the right answer, possibly
indefinitely.

### Tier 3 — Full cloud with a background worker (documented, not scheduled)

True hardware-independent cloud hosting on Render. This is the only tier that requires a
real refactor — detailed in §4. Move to it only when a trigger in §5 fires.

---

## 3. Why SignalRipper can't simply "go on Render" today

The blocker is structural, not a configuration detail. SignalRipper runs an audit
*inside the HTTP request*: the browser asks for an audit, the server runs all 8 phases —
10 to 15 minutes — and only then responds, streaming progress over SSE in the meantime.

Render's web services close connections long before 15 minutes elapse. Render's own
supported answer for long jobs is a **background worker**: a second process that runs the
slow work *outside* any HTTP request. SignalRipper has no such process — by design, per
its locked architectural decisions, the job queue is in-memory and single-user. So
"deploy to Render" is not a deployment task; it is an architecture change. That change is
§4.

---

## 4. The background-worker refactor (Tier 3 in detail)

Today the pipeline is **synchronous**: `request → run all 8 phases → respond`. The
refactor makes it **asynchronous**:

```
  request  →  enqueue a job  →  respond immediately ("job #123 started")
                   │
                   ▼
            job queue (Redis)
                   │
                   ▼
        worker process  →  runs the 8 phases  →  writes results to R2 + DB
                   │
                   ▼
   frontend polls / streams job #123 status until it reads "complete"
```

A **background worker** is simply a second program that does no HTTP at all — it watches
the queue, picks up jobs, runs them, and records the outcome. The web service stays fast
and responsive because it never runs the slow work itself; it just hands jobs off.

Concretely, Tier 3 requires:

1. **Split the pipeline out of the request.** The audit runner becomes a job the web
   service enqueues instead of calling directly.
2. **Add a real job queue.** Upstash Redis (free tier: ~500K commands/month). Replaces
   the in-memory queue so job state survives restarts and is visible to a separate
   process.
3. **Add the worker process.** A Render **Background Worker** service (paid — no free
   tier for workers) running the audit runner against the queue.
4. **Move audit bins to R2.** Render containers have ephemeral disk; anything written
   locally vanishes on redeploy. Bins must be written to Cloudflare R2 (free tier: 10 GB,
   $0 egress), and the GUI's bin-browser must read from R2.
5. **Replace headless Chrome with WeasyPrint** for PDF rendering. Chromium needs
   ~1.5–2 GB RAM per render and is fragile in slim containers; WeasyPrint is Python-native
   and ~10× lighter, but the PDF templates must be restyled to its CSS Paged Media
   strengths (running headers/footers, page numbers) and away from Flexbox/Grid.
6. **Move API keys to the host's secret manager** instead of `data/settings.json`.

**Rough cost:** Render web service (~$7/mo) + Render background worker (~$7/mo) ≈
**$14/mo**, with Upstash and R2 inside their free tiers. Effort: a multi-day refactor,
with the WeasyPrint template restyle as the largest single piece.

This is real work for a real benefit — but the benefit (hardware independence, uptime
without your involvement) only matters once SignalRipper has users who depend on it. Until
then, Tier 2 delivers the same shareability at $0 and zero refactor.

---

## 5. Triggers to move to Tier 3

Move from the dedicated-machine tunnel to full cloud when **any** of these is true (these
extend `REMOTE-HOSTING.md` §6):

1. SignalRipper becomes a **paid product with paying clients** — uptime expectations make
   a dependence on your own hardware unacceptable.
2. The collaborator group grows past ~10, or includes people who must run audits on a
   schedule you cannot personally guarantee the dedicated machine will honor.
3. You need audits triggered **programmatically** — cron, webhook, API — without any of
   your machines being involved.
4. The dedicated machine proves unreliable in practice (power, network, hardware age) and
   babysitting it costs more attention than $14/mo would.

Until one fires, Tier 2 is the correct architecture — not a stopgap.

---

## 6. How this maps to the Kit

When SignalRipper's tunnel deployment is proven on the dedicated machine, the generic
parts become the Kit's **interactive-tool deployment playbook**: the tunnel setup, the
Cloudflare Access pattern, the dedicated-host spec. ScriptRipper's Render deployment
(`ScriptRipper_Re-Do/docs/deployment/`) becomes the Kit's **unattended-tool playbook**.
The Kit's scaffolding process holds both and routes a new Ripper to one of them with the
single runtime-shape question from §1. That is the universal-framework / parametric-host
model in practice.
