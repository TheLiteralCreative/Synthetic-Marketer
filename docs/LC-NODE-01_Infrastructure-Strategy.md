# LC-NODE-01 — Infrastructure Architecture & Organizational Strategy

> **Version 2.0 — unified, multi-agent-reviewed.**
> **Date:** 2026-05-24
> **Supersedes:** the original `LC-NODE-01_Infrastructure-Arcitechture_Org-Strategy.md` draft.
> **Status:** approved working strategy for the LC-NODE-01 build.

---

## How to read this document

This is the single source of truth (SSOT) for what the repurposed 2015 iMac —
**LC-NODE-01** — is, how it is organized, and how it grows. It is a *synthesis* of two
contributions, and it is worth knowing which is which:

- The **original draft** was written by a scoped "fresh-eyes" agent asked to look past
  the immediate SignalRipper deployment and frame the machine as one node in a larger
  eventual deployment. That framing was valuable and most of it is carried forward intact.
- The **amendments** were made by the agent with full Media Rippers project context —
  the one that wrote `DEDICATED-HOST-SETUP.md`, `HOSTING-ROADMAP.md`, and
  `PRINCIPLE_universal-not-uniform.md`. Where the original draft's general advice
  collided with a concrete fact about *this* machine or *this* toolchain, the amendment
  wins, and the reasoning is written down so the decision never has to be re-litigated.

Three amendments were made. They are applied throughout and also summarized, with full
justification, in the section **"The three amendments"** near the end. The rest of the
document is the unified strategy as it now stands.

---

## 1. What this machine is

LC-NODE-01 is no longer a personal workstation. It is being repurposed into a persistent
infrastructure node — a small, always-on machine that does a defined set of jobs
reliably, indefinitely, with nobody sitting at it.

It should **not** be treated as a personal desktop, a generic workstation, or a
dumping ground for projects. It should be treated as a lightweight server: an
orchestration node, a persistent application host, a local AI utility machine — an
*infrastructure appliance*.

This is the same conclusion `DEDICATED-HOST-SETUP.md` reaches from the SignalRipper side.
The value of the machine is **persistence and continuity**, not raw compute. A machine
that sits in one place, plugged in, doing its jobs while you work elsewhere on your
laptop, is worth more to the program than a faster machine that is only sometimes on.

The hardware is well-matched to this: a Late-2015 27" iMac with a quad-core i7, 32 GB of
RAM, and a 500 GB SSD. Against the sizing guidance in `DEDICATED-HOST-SETUP.md`, every
resource line sits at or above the "comfortable" tier.

---

## 2. The roles LC-NODE-01 can serve

The machine can serve several functions at once. Not all are active today; this is the
menu, roughly in order of present priority.

**Role 1 — Application host (primary role today).** Persistent hosting of tools such as
SignalRipper, and later other interactive Rippers, internal dashboards, small APIs, and
webhook endpoints. This is the role the machine exists for right now.

**Role 2 — AI utility node.** Local, lightweight inference and retrieval — Ollama,
Open WebUI, local embeddings, semantic search, lightweight RAG. Constraint: quantized,
lightweight models only. This machine has no dedicated AI accelerator; large frontier
models and GPU-heavy workflows do not belong here.

**Role 3 — Automation server.** Scheduled and event-driven orchestration — workflow
runners (e.g. n8n), cron jobs, webhook orchestrators, integration glue. This may
ultimately become the node's highest-value capability. (Historical note: n8n was
deliberately *removed* from the ScriptRipper stack during its pivot to a single-service
architecture. Re-introducing it here would be a genuinely new capability on the node,
not a revival of a Ripper component — keep that boundary clear.)

**Role 4 — Media / archive server.** Asset storage, reference libraries, deliverable
archives, and similar — optionally a media server such as Jellyfin.

**Role 5 — Infrastructure gateway.** Cloudflare Tunnel, reverse proxy, SSL routing,
DNS-based service exposure, ingress. SignalRipper's tunnel is the first instance of this
role and the pattern generalizes to every interactive tool the node hosts.

**Role 6 — Development / staging node.** Test deployments, staging environments,
internal previews.

A machine doing all six well requires discipline, which is the entire point of the
rest of this document.

---

## 3. Foundational principle — keep four things separate

The organizing principle for the whole node is the separation of four concerns:

- **System** — macOS itself and machine-level configuration.
- **Services** — the long-running processes (and their persistence definitions).
- **Data** — databases, persistent state, generated runtime assets.
- **Projects** — application source code and repositories.

Letting these blur together is how servers become unmanageable: tangled dependencies,
backups that are hard to reason about, migrations that turn into archaeology. Keeping
them separate keeps the node debuggable and portable.

One refinement for *this* node: the **source-code vs. runtime-data** distinction is
correct in general, but each application already has an opinion about where its own
runtime data lives, and the right move is to **respect each app's expected location
rather than force a uniform one**. SignalRipper, for example, keeps its runtime data
(`settings.json`, the jobs database, audit bins) in a `data/` directory *inside* its
repo, which its `.gitignore` deliberately excludes from version control. The separation
principle is honored — code is tracked, data is not — but it is honored *the way the
app expects*, not by relocating `data/` somewhere the app would then have to be
reconfigured to find. Separation is the goal; uniform placement is not.

---

## 4. Filesystem layout

### 4.1 The infrastructure root — `~/srv` (amended)

All node infrastructure lives under a single dedicated root. The original draft placed
this at `/srv` — the Linux convention for service data. **On macOS that root has been
changed to `~/srv`** (i.e. `/Users/literalcreative/srv`). The structure and naming below
are otherwise exactly as the original draft proposed.

Why the change — this is **Amendment 1**, justified in full in §8:

Modern macOS keeps the root filesystem on a **read-only, cryptographically signed system
volume**. You cannot simply `sudo mkdir /srv` — it fails, and creating a true root-level
directory requires a `synthetic.conf` entry plus a reboot. Even once it exists, code in a
root-owned location needs ongoing ownership and permission management (the original
draft's `chown -R` step is a patch for a problem the location itself creates). The home
folder, by contrast, is where macOS expects a user's files, where the `launchd` *user
agents* that run our services operate without permission friction, and what Time Machine
backs up by default. Rooting the tree at `~/srv` keeps every organizational benefit the
original draft described and removes all of that friction.

### 4.2 Target directory structure

```text
~/srv
│
├── apps/              Role 1 — hosted applications, one folder per app
│   └── signalripper/      the SignalRipper repo (cloned here)
│
├── cloudflare/        Role 5 — tunnel manifests, routing notes, config copies
│
├── ai/                Role 2 — Ollama, models, embeddings, vector-db
│
├── automation/        Role 3 — workflow runners, scripts, cron, workflows
│
├── media/             Role 4 — archive, assets, references, deliverables
│
├── docker/            compose files & volumes — for containerized services ONLY
│
├── logs/              centralized service logs
│
├── backups/           local backup staging
│
└── shared/            genuinely cross-service material — templates, shared env
```

Note on `cloudflare/`: the `cloudflared` client looks for its live credentials at
`~/.cloudflared/` by default, and `DEDICATED-HOST-SETUP.md` step 4 copies them there.
So `~/.cloudflared/` holds the **live tunnel credentials**; `~/srv/cloudflare/` holds
**documentation, manifests, routing notes, and config copies** — not the live secrets.
Same per-tool-default principle as §3.

### 4.3 Build the tree incrementally, not all at once (amended)

This is **Amendment 3**. The original draft prescribed creating the entire nine-folder
tree immediately. The unified strategy is to adopt the *philosophy* now and create each
directory *when a real service is about to fill it*.

The reason: empty category folders created ahead of need tend to go stale. You forget
the filing rule you invented, and the next thing gets placed by guess instead of by
reason — which is the exact "junk drawer" outcome the structure is meant to prevent. A
folder created the day you install Ollama is a folder whose purpose is unambiguous.

Concretely, **only `~/srv/apps/` is created now**, to receive SignalRipper. `cloudflare/`,
`ai/`, `automation/`, `media/`, `docker/`, and the rest are created at the moment their
first real occupant arrives.

---

## 5. Naming conventions

Use **lowercase-kebab-case** for all infrastructure folders and service names:
`signalripper`, `process-prompter`, `open-webui`, `cloudflare-tunnel`, `vector-db`.

Avoid spaces, CamelCase, cryptic abbreviations, and **version numbers in folder names**
(version belongs in git history and tags, not in a directory name that then has to be
renamed).

One reconciliation worth noting: the SignalRipper application is delivered from a GitHub
repository still named **`Synthetic-Marketer`**. That repository is deliberately *not*
being renamed — renaming it would break git history and the established remote URL. But
the *local folder* on this node is a separate choice, and it follows the convention: the
repo is cloned into `~/srv/apps/signalripper`. So "the `signalripper` folder contains a
clone of the `Synthetic-Marketer` repo" is correct and intentional.

---

## 6. Containerization strategy (amended)

This is **Amendment 2**, and the most consequential. The original draft's guidance was
"containerize everything possible, even if it seems like overkill." The unified strategy
replaces that blanket rule with a **per-tool decision**.

### 6.1 The rule: containerize by fit, not by default

Docker is a genuinely good tool. It provides portability, reproducibility, isolation, and
easier migration — *for software that fits a container well*. The mistake is treating
"containerize everything" as a universal rule rather than asking, for each service,
whether containerization actually serves it.

The deciding question for any new service on the node is simply: **does this service run
cleanly in a Linux container, and does containerizing it cost less than it saves?**

- **Yes for most future services.** Ollama, Open WebUI, n8n, and similar tools have
  first-class Docker images and run beautifully containerized. When Roles 2 and 3 are
  built out, Docker is the right call for them, and `~/srv/docker/` is where their
  compose files and volumes live.
- **No for SignalRipper.** SignalRipper is hosted **natively** on macOS and should stay
  that way.

### 6.2 Why SignalRipper stays native

Two reasons, both already documented in the project's hosting canon:

First, **the runtime-shape rule** (`HOSTING-ROADMAP.md` §1). SignalRipper's audit is a
single 10–15 minute synchronous job with a person watching live progress. The *reason*
it is hosted on a tunnel from this Mac — rather than on a cloud platform — is that this
runtime shape wants an always-on machine it can occupy. Native macOS, with native Chrome
and `launchd`-managed services, *is* the correct host. That decision is the foundation of
the entire Phase 1 plan.

Second, **the cost is real and documented**. `HOSTING-ROADMAP.md` §4 already costed out
containerizing SignalRipper: it is a multi-day refactor, because SignalRipper drives
headless Chrome, which needs roughly 1.5–2 GB of RAM per render and is fragile inside
slim Linux containers. Containerizing it properly means tearing Chrome out and replacing
it with WeasyPrint, then restyling the PDF templates. On top of that, Docker Desktop on a
Mac runs a Linux virtual machine under the hood — it costs RAM and re-introduces the
exact headless-Chrome fragility we are deliberately avoiding.

We are most of the way through a working *native* deployment. Containerizing SignalRipper
now would mean discarding that and signing up for a multi-day refactor for no benefit we
currently need. That is textbook "shiny-object" drift — adopting a tool because it is
good in general rather than because a real deciding question pointed to it. (See
`PRINCIPLE_universal-not-uniform.md` for the program-level version of this argument.)

### 6.3 Migration portability without universal Docker

The original draft's strongest argument for containerizing everything was migration:
this iMac is transitional, and one day the node may move to a mini PC, a Linux box, an
M-series Mac, or a VPS. That concern is valid. But portability does not come *only* from
Docker. It comes from the four-way separation in §3, from each service being installed
in a documented and reproducible way, and from the infrastructure tree being a single
coherent thing to copy. Container-friendly services will migrate via Docker; SignalRipper
will migrate the way `HOSTING-ROADMAP.md` already plans — and if a true cloud move is
ever warranted, the Tier 3 refactor in §4 of that document *is* the containerization
plan, executed deliberately when a trigger fires, not pre-emptively tonight.

---

## 7. Storage allocation

**Internal SSD** (the 500 GB drive) — macOS, active services, application source,
`launchd`/service definitions, configs, Docker runtime, and lightweight persistent data.

**External SSDs** (added as needed) — AI models, media libraries, archives, backups,
large Docker volumes, vector databases, and long-term storage. The internal drive is
generous for the application-host role; large-footprint roles (AI models especially)
should land on external storage so the system drive never gets tight.

---

## 8. The three amendments — summary and justification

For the record, so these decisions never have to be re-derived:

**Amendment 1 — infrastructure root is `~/srv`, not `/srv`.**
*Justification:* macOS keeps the root filesystem read-only and signed; `/srv` cannot be
created with a plain `sudo mkdir` and would require a `synthetic.conf` entry plus a
reboot, then ongoing ownership management. The home folder is where macOS, `launchd`
user agents, and Time Machine all expect user files. `~/srv` keeps the original draft's
entire structure and naming and removes all OS friction. This is the
"universal, not uniform" principle in action: a Linux convention applied unchanged to a
Mac is forced uniformity; the universal goal (clean separation) is better met the
macOS-native way.

**Amendment 2 — containerization is a per-tool decision, not a blanket rule.**
*Justification:* SignalRipper is hosted natively because the runtime-shape rule
(`HOSTING-ROADMAP.md` §1) makes native macOS its correct host, and because
`HOSTING-ROADMAP.md` §4 documents that containerizing it is a multi-day refactor (headless
Chrome is heavy and fragile in containers). Docker remains the right tool for
container-friendly future services (Ollama, Open WebUI, n8n). The rule is: containerize
by fit, decided per service, not by default.

**Amendment 3 — build the directory tree incrementally.**
*Justification:* empty category folders created ahead of need go stale and invite
filing-by-guess — the junk-drawer outcome the structure exists to prevent. Adopt the
philosophy now; create each directory when its first real occupant arrives. Only
`~/srv/apps/` is created at the outset.

All three amendments share one root idea: a strategy should be **universal** (one
coherent framework, one set of deciding questions) without being **uniform** (the same
choice forced everywhere regardless of fit). That idea is documented at program level in
`PRINCIPLE_universal-not-uniform.md`, and it is the through-line of this node strategy.

---

## 9. Relationship to existing project canon

This document does not stand alone. It sits alongside:

- **`DEDICATED-HOST-SETUP.md`** — the step-by-step build spec for this exact machine
  (energy settings, runtimes, copying the repo and credentials, `launchd` persistence,
  the SSE smoke test). LC-NODE-01 *is* the "dedicated host" that document describes.
- **`HOSTING-ROADMAP.md`** — the three-tier hosting plan and the runtime-shape rule that
  determines what is hosted natively here versus elsewhere.
- **`PRINCIPLE_universal-not-uniform.md`** — the program-level principle underpinning all
  three amendments above.

Where this document and those documents touch the same subject, they agree by design.

---

## 10. Immediate next steps

1. **Create `~/srv/apps/`** — the only part of the tree built now.
2. **Clone SignalRipper** into `~/srv/apps/signalripper`.
3. **Copy the two secret files** the repo does not carry — `data/settings.json` (the
   Anthropic API key) and the `~/.cloudflared/` tunnel credentials — from the laptop.
4. **Install SignalRipper's Python dependencies** in a virtual environment.
5. **Smoke-test by hand** — start SignalRipper and the tunnel manually; confirm
   `signalripper.literalcreative.com` loads through the Cloudflare Access gate.
6. **Make both services persistent** with `launchd` user agents (start on boot, restart
   on crash).
7. **Run the non-skippable SSE smoke test** through the public URL.
8. **Decommission the laptop tunnel** so exactly one machine answers it.

Steps 1–8 follow `DEDICATED-HOST-SETUP.md` directly. Roles 2–6 are future work, each
built incrementally per §4.3 when its time comes.

---

## 11. Scope and location note

Like `PRINCIPLE_universal-not-uniform.md` and `HOSTING-ROADMAP.md`, this is a
program-level document that currently lives in `Synthetic-Marketer/docs/` because that
is where the LC-NODE-01 work is happening and where its companion specs already sit. It
belongs with the Media Rippers Kit / strategy documentation, and should be relocated
there when those repositories are in reach. Until then, this is its home and it is the
SSOT for the node.
