# Synthetic-Marketer Backlog

Ideas considered but deferred. Each has been judged "would add real quality if added" but is not blocking the GUI build. Keep this list updated when new ideas surface.

---

## Active backlog

### 1. Search Console / Analytics integration
**Adds:** Real baseline data for traffic, conversion, top queries, top landing pages. Calibrates the revenue-impact estimates from "plausible" to "specific."
**How:** Per-audit opt-in. User provides Google Search Console API access (OAuth) for the audit subject; script reads top-20-queries, top-20-pages, click-through-rate, indexed-page-count.
**Effort:** Medium (~half-day). OAuth flow + GSC API integration in a new `tools/gsc.py` script.
**Status:** Deferred. Re-engage when an audit is for a brand the user has GSC access to.

### 2. Auth-walled site support
**Adds:** Ability to audit logged-in product surfaces (SaaS dashboards, member areas, gated content). Currently any auth wall ends discovery.
**How:** Extend `tools/discover.py` to accept a session cookie or HTTP basic auth via env var or flag. Pass headers through to curl.
**Effort:** Small (~1-2 hours). The fetcher in `discover.py` already wraps curl; just add header passthrough.
**Status:** Deferred. Add when an audit subject requires it.

### 3. Brand voice profile deliverable
**Adds:** A separate `BRAND-VOICE.md` deliverable formalizing tone, register, vocabulary, sentence length, voice rules, do/don't list. Feeds downstream content generation (especially AI-assisted content).
**How:** New subagent run after the audit. Reads source-site copy, identifies recurring patterns, codifies the voice. Becomes part of the standard deliverable set.
**Effort:** Small (~1 hour to spec + integrate into pipeline).
**Status:** Deferred. Highest value when the audit will be followed by content production.

### 4. Re-audit / delta tracking
**Adds:** Mechanism to compare an audit run today vs. a future re-audit on the same site. Quantifies which recommendations got implemented, which findings persisted, and how the overall score changed.
**How:** New `tools/delta.py` that takes two bin paths and produces `DELTA-REPORT.md` showing score deltas per category, finding closures (resolved / still-open), and recommendation implementation status.
**Effort:** Medium (~half-day).
**Status:** Deferred. Highest value for retainer-style ongoing client relationships.

### 5. Search volume / competitive data
**Adds:** Volume estimates for keyword recommendations, traffic estimates for competitors. Calibrates which keyword clusters are worth pursuing.
**How:** Either (a) Free tier of Google Keyword Planner (requires Ads account, no API), (b) Bing Webmaster Tools (free, has API), or (c) paid (Ahrefs / Semrush APIs, real money).
**Effort:** Variable. Free options ~1 day; paid options ~half-day but recurring cost.
**Status:** Deferred. Revisit if budget allows or if many audits start needing volume calibration.

### 6. Industry benchmarks library
**Adds:** Calibrates findings against industry medians instead of generic best practices. "Your conversion rate is 1.2%, B2B fintech median is 2.4%" beats "your conversion is low."
**How:** A maintained `tools/benchmarks.json` file with per-business-type expected ranges (Core Web Vitals, conversion rate, schema coverage, blog post cadence, review counts). Audit subagents reference it when scoring.
**Effort:** Small initial (~1 hour to seed) + ongoing maintenance to keep current.
**Status:** Deferred. Worth seeding once we have ~5-10 audits to extract benchmark data from.

### 7. Visual evidence (screenshots)
**Adds:** Embedded screenshots of key pages in the audit deliverables. Especially valuable for local/retail audits where the storefront / layout / hero matter as much as the copy.
**How:** Headless Chrome (already installed for `md_to_pdf.py`) — capture full-page screenshots of homepage + 3-5 key pages during discovery. Save to `bin/screenshots/`. Embed thumbnails in MARKETING-AUDIT.md.
**Effort:** Small (~1-2 hours). Chrome headless `--screenshot` flag.
**Status:** Deferred. Highest value for local / retail / hospitality audits.

### 8. Output format extensions (Notion, Google Docs, slide decks)
**Adds:** Native output formats beyond markdown + PDF. Notion DB sync for ongoing client work, Google Docs for collaborative review, slide decks for client presentations.
**How:** Per-format extension to the existing rendering pipeline. Notion via REST API; Google Docs via Drive API; slides via python-pptx or Google Slides API.
**Effort:** Medium per format (~1 day each). Notion is probably highest value first.
**Status:** Deferred. Wait until a client actually requests one of these formats — guessing-ahead is over-engineering.

---

## Decision log

When a backlog item becomes a "yes, build it now," document the decision here:

- 2026-05-08: Built items 1 (Lighthouse via PSI) and 2 (QA pass agent) ahead of GUI work. They were the two ideas judged most likely to materially change deliverable quality. Original list of 10 ideas — 2 promoted, 8 remain in backlog above.

- 2026-05-08: GUI shipped (B1–B5). FastAPI + React, single-command launch. All `tools/` scripts remain runnable headless; the GUI just wraps them.

- 2026-05-08: Mid-flight fix — `tools/discover.py` v0.3.0 surfaces page content excerpts (testimonials, blockquotes, hero copy) in `_DIGEST.md`. The original metadata-only digest was systematically blind to actual prose, causing the Brand & Trust subagent to miss a prominent testimonial on a real audit (hewittgc.com). Promoted "real content in digest" from latent issue to shipped fix.

- 2026-05-08: Three runtime bugs fixed during real-use shakedown:
  1. Cost meter inflated due to SSE replays double-counting cost events. Backend now emits cumulative totals; frontend reducer SETs (no longer ADDs); EventSource closes itself on `done`/`error`.
  2. Brand-name input wasn't sanitized before bin folder creation. `&` and other unsafe chars now stripped/replaced before `Synth-mkt_<Brand>_<date>` is formed.
  3. QA cross-audit-reference regex was too loose ("across all communications. Audit finding..." false-positively tripped). Tightened to require `audits?` within ≤2 words of trigger phrase.

- 2026-05-08: Added per-audit cost heads-up — after Phase 1 completes, the runner emits an estimated cost for Phases 2–8 based on digest size + selected model. Calibrated against two real Haiku audits ($0.26 small / $1.02 medium-large). Not a confirmation gate — just visibility before the expensive part runs.
