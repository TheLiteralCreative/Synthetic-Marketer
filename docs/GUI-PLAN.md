# GUI Build Plan — Synthetic-Marketer

**Status:** Approved 2026-05-08. Active build plan-of-record.

A complete spec for the local-first audit interface.

---

## Executive summary

Build a **local FastAPI + React app** that wraps the existing audit pipeline. Run-by-default on `localhost:8000`, single Python entrypoint to start. Uses the **Claude Agent SDK with `bypassPermissions`** so audits run from start to finish without permission prompts. Inherits every tool we built (`discover.py`, `qa.py`, `md_to_pdf.py`) and every skill (`/market audit`, `/market report-pdf`) without modification — the GUI is a shell, not a rewrite.

---

## Architecture decisions

| Decision | Choice | Why |
|---|---|---|
| **Foundation** | Claude Agent SDK (Python), `permissionMode: 'bypassPermissions'` | Inherits skills + subagents + tools without rewrite. Zero permission prompts. ~10x less code than reimplementing. |
| **Backend** | FastAPI | Single deployment unit. Async-first (good for streaming progress). |
| **Frontend** | React (Vite) served by FastAPI | Build to `frontend/dist/`, FastAPI mounts it as static. |
| **Hosting** | Local-first, deployable later | Personal tool; API key stays on the machine; zero recurring cost. Render path stays available if remote access ever wanted. |
| **State** | SQLite + filesystem (project bins are the source of truth) | No external DB. Audits are already self-contained folders — let the filesystem be the database. SQLite stores only job state and metadata. |
| **Progress streaming** | Server-Sent Events (SSE) | Simpler than WebSockets, works through any reverse proxy, native browser support. |
| **Pipeline integration** | In-process Python | Tools are already structured as functions; import them directly, hook progress callbacks. Subprocess approach would be awkward for LLM phases. |

**Cross-platform:** Mac primary, Windows/Linux supported (one-time fix to `md_to_pdf.py` Chrome-path detection).

---

## UI plan

Three views, single-page app, sidebar nav.

### View 1 — New Audit (default landing)

URL input + brand-name override + skip-PSI toggle + strict-QA toggle + Run Audit button + estimated-time hint.

### View 2 — In-Progress (during run)

Phase-by-phase status (8 phases) with live timestamps. Subagent-level breakdown for Phase 2 (5 parallel categories). Live log stream (collapsible). Cancel button.

### View 3 — Audit Detail (when complete, or viewing past)

Score gauge + grade + QA status badge. Category breakdown (visual bars). Findings preview (top 5). Deliverable list (one-click open). Open-bin-folder button. Re-render-PDFs button.

### Sidebar — All Audits view

Simple list of past bins with score, date, status. Sortable by date / score / domain.

### Settings panel

- Anthropic API key (OS keychain or `.env`, never committed)
- PageSpeed Insights API key (optional, for production audit volume)
- Default output folder
- Theme (light/dark)
- Cost-tracking toggle

---

## Technical architecture

```
Synthetic-Marketer/
├── tools/                           # UNCHANGED (production)
│   ├── discover.py                  # imported as a module
│   ├── qa.py                        # imported as a module
│   └── md_to_pdf.py                 # imported as a module
│
├── backend/                         # NEW
│   ├── main.py                      # FastAPI app entry
│   ├── audit_runner.py              # Pipeline orchestration (uses Agent SDK)
│   ├── routes.py                    # API endpoints
│   ├── job_queue.py                 # Background job tracking
│   ├── progress.py                  # Phase tracking + SSE streaming
│   ├── settings.py                  # Config persistence
│   ├── db.py                        # SQLite (jobs table only)
│   └── models.py                    # Pydantic models
│
├── frontend/                        # NEW
│   ├── package.json                 # Vite + React + Tailwind
│   ├── src/
│   │   ├── App.jsx                  # Top-level routing
│   │   ├── views/                   # NewAudit, InProgress, AuditDetail, AllAudits, Settings
│   │   ├── components/              # ScoreGauge, PhaseTimeline, FindingCard, etc.
│   │   ├── lib/api.js               # fetch + SSE wrappers
│   │   └── styles/                  # Tailwind config + theme
│   └── dist/                        # Build output, served by FastAPI
│
├── data/                            # gitignored
│   ├── jobs.db                      # SQLite
│   └── settings.json                # user config
│
├── start.py                         # NEW: single-command launcher
└── pyproject.toml                   # NEW: Python deps + entry points
```

### Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/audits` | Start a new audit, returns `job_id` |
| `GET` | `/api/audits/{job_id}/stream` | SSE stream of progress events |
| `POST` | `/api/audits/{job_id}/cancel` | Kill a running audit |
| `GET` | `/api/audits` | List all bins on disk + their status |
| `GET` | `/api/audits/{bin_name}` | Get audit metadata (score, findings preview, file list) |
| `POST` | `/api/audits/{bin_name}/rerender` | Re-run `md_to_pdf.py` on a bin |
| `POST` | `/api/audits/{bin_name}/open-folder` | Open bin folder in Finder/Explorer |
| `GET` | `/api/files/{bin_name}/{filename}` | Stream a deliverable file (PDF or markdown) |
| `GET` | `/api/settings` | Read settings |
| `PUT` | `/api/settings` | Update settings |

### Pipeline runner (the load-bearing piece)

`backend/audit_runner.py` orchestrates the 8-phase pipeline using the Claude Agent SDK with progress callbacks:

```python
async def run_audit(url, bin_dir, on_progress):
    on_progress(phase=1, status="running")
    discover.discover(url, bin_dir, do_psi=True)
    on_progress(phase=1, status="done")

    on_progress(phase=2, status="running")
    await spawn_audit_subagents(bin_dir, on_progress)

    # ... Phase 3-8
```

Phases 1, 6, and 8 are pure Python (no LLM). Phases 2, 3, 4, 5, 7 use the Agent SDK with the existing skills.

---

## Build phases

| Phase | What | Output |
|---|---|---|
| **B1 — Foundation** | FastAPI + React scaffold, settings persistence, SQLite, ping endpoint | App starts on `localhost:8000`, frontend renders |
| **B2 — Pipeline runner** | `audit_runner.py`, Agent SDK integration, progress callback system | Can run a complete audit from CLI |
| **B3 — New Audit + In-Progress UI** | Form view + SSE-driven progress view, cancel button | Can run an audit from the browser, watch it complete |
| **B4 — Audit Detail + All Audits views** | Score gauge, findings preview, deliverable links, past-audits list | Can browse, open, and re-render past audits |
| **B5 — Polish** | Design system match, settings panel, error handling, README updates, demo recording | Production-ready local tool |

---

## Risks and open questions

| Risk | Mitigation |
|---|---|
| Claude Agent SDK skill-invocation behavior unverified live | First task in B2 is a smoke test — invoke `/market report-pdf` against an existing bin. Fallback: read skill markdowns and replay as Anthropic SDK calls. |
| Concurrent audits | MVP is single-audit-at-a-time. Job queue is structured to support parallel runs later but not exposed. |
| API cost per audit | Add a cost estimator in Settings (track tokens, multiply by model price). Display per-audit cost on completion. |
| Cross-platform Chrome path | `md_to_pdf.py` currently checks 5 candidate paths (mostly macOS). Add Windows + Linux paths in B5. |
| Session lost mid-audit | SSE auto-reconnects; job state persists in SQLite; audit continues in background and shows in All Audits when complete. |
| API key storage | OS keychain via `keyring` Python package where possible, fallback to `.env` (gitignored). Never log or transmit. |

---

## Acceptance criteria

- [ ] Single command starts the app (`python start.py` or `./start.sh`)
- [ ] Browser opens to `localhost:8000` with the New Audit form
- [ ] Entering a URL and clicking Run Audit produces a complete project bin in 10–15 minutes
- [ ] Pipeline runs without permission prompts
- [ ] Progress is visible in real time
- [ ] All 7 markdowns + dashboard PDF + bundled PDF + QA report produced
- [ ] User can re-open any past audit and see its score, findings, and deliverables
- [ ] User can open any deliverable PDF with one click
- [ ] User can re-render PDFs from the UI without touching the terminal
- [ ] Settings persist across sessions
- [ ] Audit cost is reported on completion
- [ ] App runs on Mac (primary target)
- [ ] No regressions to the existing tools (`discover.py`, `qa.py`, `md_to_pdf.py` continue to work standalone)

---

## Out of scope (deferred)

- Multi-user authentication (it's a personal tool)
- Cloud deployment (local-first; deploy later if needed)
- Mobile-responsive design (desktop-first MVP)
- In-browser editing of deliverables (use the file system)
- Webhooks / external API access
- Theme customization beyond light/dark
- Multi-tenancy / per-client workspaces
- Backlog items 1–8 from `tools/BACKLOG.md`
