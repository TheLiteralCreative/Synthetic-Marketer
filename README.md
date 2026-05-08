# Synthetic-Marketer

A marketing audit pipeline that produces shareable, client-ready deliverables for any website in 10–15 minutes.

The tool replaces 6–8 hours of manual marketing-audit work — site discovery, schema validation, competitor research, persona definition, scoring, and PDF rendering — with a sequenced pipeline of automated discovery scripts and parallel LLM subagents. Outputs are designed to be sent directly to a client without further editing.

---

## What it produces

For every audit run, Synthetic-Marketer produces a date-stamped project bin containing:

| Deliverable | Format | Purpose |
|---|---|---|
| `EXECUTIVE-BRIEF` | `.md` + `.pdf` | One-page TL;DR for skimmers and stakeholders |
| `WALKTHROUGH` | `.md` + `.pdf` | Narrated tour of the audit, plain-language |
| `MARKETING-AUDIT` | `.md` + `.pdf` | Full 6-category scorecard with detailed analysis |
| `COMPETITOR-REPORT` | `.md` + `.pdf` | Deep competitive intelligence, comparison matrices |
| `ADS-AUDIENCE` | `.md` + `.pdf` | 5–7 personas with channel allocation and creative hooks |
| `IMPLEMENTATION-ROADMAP` | `.md` + `.pdf` | 90-day execution plan with effort × impact ranking |
| `GLOSSARY` | `.md` + `.pdf` | Audit-specific terminology reference |
| `MARKETING-REPORT-<domain>.pdf` | dashboard PDF | Score gauge, bar chart, findings table — client cover deliverable |
| `FULL-REPORT.pdf` | bundled PDF | All 7 markdowns rendered into one document with cover + TOC |
| `_DIGEST.md` | facts | Auto-generated discovery digest (subagent input) |
| `_DISCOVERY-NOTES.md` | checklist | Auto-generated pass/fail markers per discovery check |
| `_QA-REPORT.md` | report | Pre-shipping quality assurance (10 mechanical checks) |
| `raw/*.html` | cache | Cached HTML for every fetched page (audit reproducibility) |

Each audit produces a **composite Marketing Score (0–100)** weighted across six categories: Content & Messaging (25%), Conversion Optimization (20%), SEO & Discoverability (20%), Competitive Positioning (15%), Brand & Trust (10%), Growth & Strategy (10%).

---

## Quickstart

```bash
# 1. Create a date-stamped project bin
BIN="Synth-mkt_<Brand>_$(date +%Y%m%d)"
mkdir "$BIN"

# 2. Run discovery (fetches site, validates schema, runs PageSpeed Insights)
python3 tools/discover.py https://target-site.example.com "$BIN"

# 3. Run the audit pipeline (5 parallel subagents)
#    Currently runs inside Claude Code via the /market audit skill.
#    A standalone CLI / GUI is in development.

# 4. After deliverables are written, run QA pass
python3 tools/qa.py "$BIN"

# 5. Generate the dashboard PDF
#    Currently runs via /market report-pdf skill

# 6. Render human-friendly PDFs of every markdown
python3 tools/md_to_pdf.py "$BIN"
```

The pipeline is designed for **personal-tool use** — run by a trusted operator against websites the operator wants to analyze. It is not currently designed as a multi-tenant SaaS.

---

## Pipeline phases

| Phase | What happens | Output |
|---|---|---|
| 0 | Create project bin | empty folder |
| 1 | **Discovery** — site crawl, schema validation, PSI / Lighthouse, robots.txt analysis | `_DIGEST.md`, `_DISCOVERY-NOTES.md`, `raw/*.html` |
| 2 | **5 parallel audit subagents** — Content, Conversion, SEO, Competitive, Brand+Growth | scored category analyses |
| 3 | **Aggregate audit** — composite score, prioritized findings, action plan | `MARKETING-AUDIT.md` |
| 4 | **Companion reports** (parallel) — Competitor + Audience | `COMPETITOR-REPORT.md`, `ADS-AUDIENCE.md` |
| 5 | **Standard companion deliverables** — Brief, Walkthrough, Roadmap, Glossary | `EXECUTIVE-BRIEF.md`, etc. |
| 6 | **QA pass** — automated consistency and rule-compliance checks | `_QA-REPORT.md` |
| 7 | **Dashboard PDF** — score gauge, bar chart, executive cover | `MARKETING-REPORT-<domain>.pdf` |
| 8 | **Human-friendly PDFs** — per-markdown styled rendering + bundled FULL-REPORT | per-markdown PDFs + `FULL-REPORT.pdf` |

**Wall-clock target:** 10–15 minutes end-to-end. Most of the time is the parallel subagent runs in Phases 2 and 4, plus the PageSpeed Insights API calls in Phase 1.

For the full pipeline specification, hard rules, voice rules, and the discovery checklist, see [`tools/AUDIT-PROCESS.md`](tools/AUDIT-PROCESS.md).

---

## Tool inventory

| File | Role |
|---|---|
| [`tools/discover.py`](tools/discover.py) | Automated discovery — site crawl, schema validation, robots.txt audit, PageSpeed Insights via Lighthouse API, NAP extraction, social-link inventory |
| [`tools/qa.py`](tools/qa.py) | Pre-shipping QA pass — 10 mechanical checks for cross-audit refs, score consistency, brand-name leakage, broken links, placeholder content |
| [`tools/md_to_pdf.py`](tools/md_to_pdf.py) | Markdown-to-PDF rendering via headless Chrome — produces per-markdown PDFs and a bundled FULL-REPORT.pdf with cover + TOC |
| [`tools/AUDIT-PROCESS.md`](tools/AUDIT-PROCESS.md) | Full pipeline specification — file naming, hard rules (incl. the no-cross-audit-references rule), discovery checklist, QA checks |
| [`tools/BACKLOG.md`](tools/BACKLOG.md) | Deferred enhancements with effort estimates and decision log |

---

## Hard rules

The pipeline enforces a small set of non-negotiable rules. The most important:

**Rule 1 — Self-contained audits.**
Every project bin must read as a self-contained, independently-shareable audit. Documents are routinely sent to clients, partners, or new team members who have no awareness of any other audit produced by the operator. Cross-audit references ("the lowest score we've seen," "compared to Brand X's audit," etc.) are forbidden — `tools/qa.py` enforces this with regex pattern matching.

This matters because: deliverables are sent to clients. Clients should not see references to other clients' audits. The QA pass catches violations before shipping.

For the full rule set, see [`tools/AUDIT-PROCESS.md`](tools/AUDIT-PROCESS.md).

---

## Configuration

### PageSpeed Insights (recommended)

Anonymous PSI is rate-limited aggressively (often 429 after 1–3 calls). For production audits, set a free Google Cloud API key:

```bash
export PAGESPEED_API_KEY="<your-google-api-key>"
```

A free PSI API key gives 25K queries/day. Without one, the discovery script retries with exponential backoff and degrades gracefully if all retries fail (the audit still runs, just without performance metrics).

### Skip PSI entirely

```bash
python3 tools/discover.py <url> <bin> --no-psi
```

### Adjust PSI page count

```bash
python3 tools/discover.py <url> <bin> --psi-pages 5
```

Default is 3 pages (homepage + 2 highest-priority interior pages selected by URL heuristic).

---

## Requirements

| Component | Used for | Install |
|---|---|---|
| Python 3.10+ | All scripts (`discover.py`, `qa.py`, `md_to_pdf.py`) | system |
| `markdown` Python package | HTML rendering for PDFs | `pip install markdown` |
| `reportlab` Python package | Dashboard PDF generation | `pip install reportlab` |
| Google Chrome | Headless rendering for PDFs | system app |
| `curl` | Page fetching with realistic User-Agent | system |
| Claude Code (currently) | LLM subagent orchestration in Phases 2, 3, 4, 5 | `claude.com/code` |

A standalone CLI / GUI that decouples the pipeline from Claude Code interactive use is in development — see [`tools/BACKLOG.md`](tools/BACKLOG.md).

---

## Output example

A typical project bin after a complete audit:

```
Synth-mkt_<Brand>_<YYYYMMDD>/
├── _DIGEST.md                     ← auto-generated discovery facts
├── _DISCOVERY-NOTES.md            ← auto-generated checklist (pass/fail)
├── _QA-REPORT.md                  ← pre-ship quality-assurance report
├── EXECUTIVE-BRIEF.md             ← TL;DR for stakeholders
├── EXECUTIVE-BRIEF.pdf
├── WALKTHROUGH.md                 ← narrated tour of the audit
├── WALKTHROUGH.pdf
├── MARKETING-AUDIT.md             ← full 6-category scorecard
├── MARKETING-AUDIT.pdf
├── COMPETITOR-REPORT.md           ← competitive intelligence
├── COMPETITOR-REPORT.pdf
├── ADS-AUDIENCE.md                ← personas + targeting + creative hooks
├── ADS-AUDIENCE.pdf
├── IMPLEMENTATION-ROADMAP.md      ← 90-day execution plan
├── IMPLEMENTATION-ROADMAP.pdf
├── GLOSSARY.md                    ← audit-specific terminology
├── GLOSSARY.pdf
├── MARKETING-REPORT-<domain>.pdf  ← dashboard PDF (client cover)
├── FULL-REPORT.pdf                ← bundled PDF with cover + TOC
└── raw/                           ← cached HTML from discovery
    ├── home.html
    ├── about.html
    └── ...
```

---

## Status

| Component | Status |
|---|---|
| Discovery script (`discover.py`) | ✅ v0.2.0 — production |
| QA pass (`qa.py`) | ✅ v0.1.0 — production |
| PDF rendering (`md_to_pdf.py`) | ✅ production |
| Audit pipeline (subagent orchestration) | ✅ runs inside Claude Code |
| Standalone CLI / GUI | 🚧 in development |
| Performance metrics (Lighthouse / PSI) | ✅ integrated, requires API key for production |
| Search Console / Analytics integration | 📋 backlog |
| Re-audit / delta tracking | 📋 backlog |

See [`tools/BACKLOG.md`](tools/BACKLOG.md) for the full deferred-features list.

---

## License

Private tooling. Not currently licensed for redistribution.
