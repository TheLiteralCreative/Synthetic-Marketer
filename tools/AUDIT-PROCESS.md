# Synthetic-Marketer Audit Process

The complete pipeline spec for producing a marketing audit deliverable bundle. Read this before kicking off a new audit; rules below are non-negotiable unless explicitly waived in advance.

---

## 1. Pipeline overview

A complete audit produces **7 markdown deliverables + matching PDFs + 1 dashboard summary PDF + 1 bundled FULL-REPORT PDF + 1 QA report** in a date-stamped project bin.

| Phase | What | Tool / Skill | Output |
|---|---|---|---|
| 0 | Create project bin | `mkdir Synth-mkt_<Brand>_<YYYYMMDD>` | empty folder |
| 1 | Discovery (incl. Lighthouse via PSI) | `python3 tools/discover.py <url> <bin>` | `bin/_DIGEST.md`, `bin/_DISCOVERY-NOTES.md`, `bin/raw/*.html` |
| 2 | 5 parallel audit subagents | spawned by `/market audit` orchestration logic | scored analysis per category |
| 3 | Aggregate audit | hand-written | `bin/MARKETING-AUDIT.md` |
| 4 | Companion reports (parallel) | 2 spawned agents | `bin/COMPETITOR-REPORT.md`, `bin/ADS-AUDIENCE.md` |
| 5 | Standard companion deliverables | hand-written using audit + reports | `EXECUTIVE-BRIEF.md`, `WALKTHROUGH.md`, `IMPLEMENTATION-ROADMAP.md`, `GLOSSARY.md` |
| 6 | **QA pass** | `python3 tools/qa.py <bin>` | `bin/_QA-REPORT.md` (must be 0 critical before shipping) |
| 7 | Dashboard PDF | `/market report-pdf` skill | `MARKETING-REPORT-<domain>.pdf` |
| 8 | Human-friendly PDFs | `python3 tools/md_to_pdf.py <bin>` | per-markdown PDFs + `FULL-REPORT.pdf` |

**Wall-clock target:** 10–15 minutes end-to-end. Most of the time is the parallel subagent runs in Phases 2 and 4 plus the PSI calls in Phase 1.

---

## 2. File naming and bin structure

**Project bin naming:** `Synth-mkt_<Brand>_<YYYYMMDD>`
- `<Brand>` is the cleanest brand-name token (e.g., `CAPSTONE`, `FlexentFreight`, `GuildHouse`)
- `<YYYYMMDD>` is the audit date in 4-digit-year-month-day format
- Hyphens within `<Brand>` are acceptable; spaces are not

**Standard files inside the bin:**

| File | Phase | Purpose |
|---|---|---|
| `_DIGEST.md` | 1 | Auto-generated discovery facts incl. PSI metrics (subagents read this) |
| `_DISCOVERY-NOTES.md` | 1 | Auto-generated checklist with pass/fail markers |
| `_QA-REPORT.md` | 6 | Auto-generated quality-assurance report (must be 0 critical before shipping) |
| `raw/*.html` | 1 | Cached HTML for every fetched page |
| `EXECUTIVE-BRIEF.md` | 5 | TLDR for skimmers |
| `WALKTHROUGH.md` | 5 | Narrated tour of the audit |
| `MARKETING-AUDIT.md` | 3 | Full 6-category scorecard |
| `COMPETITOR-REPORT.md` | 4 | Deep competitive intelligence |
| `ADS-AUDIENCE.md` | 4 | Personas + targeting + creative hooks |
| `IMPLEMENTATION-ROADMAP.md` | 5 | 90-day execution plan |
| `GLOSSARY.md` | 5 | Audit-specific terminology reference |
| `MARKETING-REPORT-<domain>.pdf` | 6 | Dashboard PDF (score gauge + bar chart + tables) |
| `EXECUTIVE-BRIEF.pdf` … `GLOSSARY.pdf` | 7 | Per-markdown human-friendly PDFs |
| `FULL-REPORT.pdf` | 7 | Bundled PDF with cover + TOC |

---

## 3. The hard rules

### Rule 1 — No cross-audit references

Each project bin must read as a **self-contained, independently-shareable audit**. Documents are routinely sent to clients, partners, or new team members who have no awareness of any other audit produced in this engagement.

**Forbidden patterns:**
- "the lowest score of any audit produced in this engagement"
- "Capstone scored 48, Flexent scored 52"
- "as observed in our previous audit"
- "this same pattern shows up on the sibling X site"
- "compared to prior audits"
- "Audited separately at `Synth-mkt_X_YYYYMMDD/`"
- "(per X audit)" or "X also identified"

**Allowed:**
- Factual market context that exists independently of any audit ("Chesapeake Bank is a $1.4B community bank with a 120-year history")
- Specific competitor details discovered through that audit's own research
- References to other deliverables **within the same bin** (e.g., "see `MARKETING-AUDIT.md` for detail")

**Edge case — sibling brands under shared parent:** If two audited brands share a parent (e.g., Capstone Banktech and Flexent Freight Funding both under Chesapeake Bank), the parent fact is allowed where directly relevant to the subject brand's positioning. The other sibling's brand name should NOT appear in the subject brand's deliverables. Sibling-brand cross-link recommendations are forbidden — neither brand should be told to publicly cross-link to the other through this audit.

**Verification:** Before shipping a bin, run:

```bash
grep -nE "(across all .*audits|both audits flagged|prior audit|previous audit|other audit|in this engagement|Synth-mkt_|of any audit produced|run to date|so far|two prior audits|sibling brand)" Synth-mkt_<Brand>_<Date>/*.md
```

Zero matches required.

### Rule 2 — Voice and tone

| Attribute | Rule |
|---|---|
| Voice | Direct, specific, opinionated. No filler. No "Great question!" or "Certainly!" |
| Length | Earn every sentence. If removing a sentence wouldn't lose information, remove it. |
| Comparisons | Use absolute observations, not relative-to-other-audits ones. ("Score: 40/100 puts the site at the D/F boundary" — not "the lowest score we've seen"). |
| Quotes | When quoting a competitor or the subject site, quote exactly. Don't paraphrase as if it were a quote. |
| Rewrites | Specific rewrites in tables (current / suggested / why), not vague "improve the headline" recommendations. |
| Severity tags | Critical / High / Medium / Low — applied to findings, with the reason the severity is what it is. |
| Hedging | If you have an opinion, state it. "I think X is right" beats "It might be worth considering whether X." |

### Rule 3 — Specificity

| Avoid | Prefer |
|---|---|
| "improve conversion" | "replace 'Submit' with 'Get My Free Quote' and add SLA microcopy below: 'We respond within 15 minutes during business hours'" |
| "your SEO is weak" | "homepage has no H1 tag and meta descriptions are duplicated on 3 of 5 pages" |
| "consider testimonials" | "lift the 4 named star testimonials currently on /freight-factoring/ to the homepage hero section" |
| "Acme Inc. should improve their content marketing" | "Launch /blog with first 4 pillar posts: '[exact title]', '[exact title]'…" |

---

## 4. The discovery checklist (now automated)

`tools/discover.py` runs this automatically and emits `_DISCOVERY-NOTES.md` with pass/fail markers. The list below is the human-readable specification of what the script checks.

### Pre-fetch
- [ ] Confirm domain resolves and returns HTTP 200
- [ ] Try www and non-www variants if the canonical version 403s or fails
- [ ] Save raw HTML to `bin/raw/` for permanent record

### Site mapping
- [ ] Fetch and parse `sitemap.xml` (including sitemap-of-sitemaps)
- [ ] Fetch and parse `robots.txt`
- [ ] Detect CMS / platform (Squarespace, WordPress, Webflow, Shopify, Next.js, Wix, HubSpot CMS, Ghost, Drupal, Joomla)
- [ ] Crawl all internal links from homepage (cap at 25 pages for breadth without runaway)
- [ ] Probe ~20 common slugs (`/blog`, `/pricing`, `/team`, `/faq`, `/events`, etc.) for 404s — these surface "missing pages" findings

### Technical signals
- [ ] Extract H1, H2, H3 from each page
- [ ] Flag pages with multiple H1 tags or zero H1 tags
- [ ] Flag pages with no headings at all
- [ ] Extract title tags + meta descriptions per page
- [ ] Flag duplicate meta descriptions across pages
- [ ] Extract all JSON-LD blocks; flatten `@graph` containers; collect all `@type` values
- [ ] Validate JSON-LD for known defects:
  - NAME field looks like a street address
  - LocalBusiness uses generic type without a specialized subtype
  - `openingHours` is malformed (empty string, comma-only string, empty array)
  - PostalAddress has city/region but no `streetAddress`
  - Organization missing `sameAs`
- [ ] Check `robots.txt` for AI crawler blocks (GPTBot, ClaudeBot, anthropic-ai, PerplexityBot, Google-Extended, Applebot-Extended, CCBot, Bytespider, etc.)
- [ ] Check `robots.txt` for AdsBot blocks (AdsBot-Google, AdsBot-Google-Mobile, AdsBot-Google-Mobile-Apps) — these damage Google Ads quality score
- [ ] Image alt-text coverage (% of `<img>` tags with non-empty alt across all pages)

### Business identity
- [ ] Phone number(s) extracted from page text
- [ ] Email addresses extracted from page text
- [ ] Postal addresses extracted from JSON-LD
- [ ] Address consistency check (canonical address count)
- [ ] Hours of operation captured

### Conversion surface
- [ ] All forms identified (count, action URL, method, fields)
- [ ] Per-form field summary (name, type, required flag, placeholder)

### External / social
- [ ] Identified social platforms linked from any page (Instagram, Facebook, X/Twitter, LinkedIn, YouTube, TikTok, Discord, Threads, Reddit, etc.)
- [ ] Identified third-party storefronts (Shopify, Square, TCGplayer, etc.)
- [ ] Identified review platforms (Yelp, Trustpilot, BBB, G2)

### Heuristic schema-need analysis
- [ ] Pages mention events/tournaments/workshops → recommend Event schema
- [ ] Commerce signals detected → recommend Product / OfferCatalog
- [ ] FAQ content present → recommend FAQPage
- [ ] Reviews/testimonials referenced → recommend Review / AggregateRating
- [ ] Local business signals → recommend LocalBusiness + PostalAddress + OpeningHoursSpecification
- [ ] Team / leadership references → recommend Person

### PageSpeed Insights (Lighthouse via PSI API)

Runs the PSI API against up to 3 conversion-relevant pages (configurable via `--psi-pages N`). Captures:
- Performance / Accessibility / Best Practices / SEO scores (0–100)
- Lab metrics: LCP, CLS, TBT, TTI, FCP, Speed Index
- Field metrics (CrUX p75, when available): LCP, INP, CLS — real-world Chrome user data
- Field overall category (FAST / AVERAGE / SLOW)

**Rate limiting:** Anonymous PSI is rate-limited aggressively (often 429 after 1–3 calls). For production use, set:

```bash
export PAGESPEED_API_KEY="<your-google-api-key>"
```

A free API key from a Google Cloud project unlocks 25K queries/day. Without one, PSI will retry with exponential backoff and degrade gracefully if all retries fail (the audit still works, just without performance metrics).

To skip PSI entirely (faster discovery): `python3 tools/discover.py <url> <bin> --no-psi`

The script outputs `_DISCOVERY-NOTES.md` with each item marked ✅ or ❌, and `_DIGEST.md` with the full structured fact set the audit subagents consume.

---

## 5. Subagent briefing rules

When spawning the 5 parallel audit subagents (Phase 2), the 2 companion-report agents (Phase 4), or any other audit-related agent:

1. **Always brief the agent on Rule 1 (no cross-audit references).** Even when the agent is briefed to use a previous audit's deliverables as a *format reference*, the output must not name or reference that previous audit's brand.
2. **Provide the digest path** (`/tmp/<run>/<DIGEST>.md` or `bin/_DIGEST.md`) and the raw HTML cache path. Do not have the agent re-fetch.
3. **State the business type and target audience** explicitly in the brief — don't assume the agent will infer it correctly from the digest.
4. **Specify the output format and length** explicitly. Subagents trail off into 5,000-word documents if not capped.
5. **Tell the agent what NOT to score on.** Each subagent has a single responsibility (Content / Conversion / SEO / Competitive / Brand+Growth) — don't let them double-score.
6. **For companion reports**, tell the agent which deliverable in the *same bin* to use as voice/structure reference (or instruct them to invent a structure if no reference exists yet — but never reference a different bin's deliverable).

---

## 6. Quality assurance before shipping

The QA pass (Phase 6) is now automated. Run:

```bash
python3 tools/qa.py Synth-mkt_<Brand>_<YYYYMMDD>
```

The script produces `_QA-REPORT.md` and exits with code:
- `0` = ✅ ready to ship — all checks passed
- `1` = ⚠️  review before shipping — warnings present (informational)
- `2` = 🛑 do not ship — critical issues found

**Checks run automatically:**

1. **Required files present** — every standard deliverable exists
2. **No cross-audit references** — Rule 1 enforcement (grep for forbidden patterns)
3. **No sibling-brand leakage** — auto-detects other `Synth-mkt_*` bins and ensures no other-bin brand names appear
4. **Overall score consistent** — same `XX/100` score in EXECUTIVE-BRIEF, WALKTHROUGH, MARKETING-AUDIT, IMPLEMENTATION-ROADMAP
5. **Six category scores present** — full breakdown table in MARKETING-AUDIT.md
6. **Internal markdown links resolve** — every `[text](path)` link in any deliverable points to a real file in the bin
7. **Phone-number consistency** — phones in subject deliverables (excludes COMPETITOR-REPORT and ADS-AUDIENCE which legitimately list competitor / persona numbers)
8. **No placeholder content** — TODO, FIXME, lorem ipsum, `[YOUR_*]` template variables, `[insert ...]`
9. **Dashboard PDF present** — `MARKETING-REPORT-<domain>.pdf` exists
10. **Human-friendly PDFs rendered** — all per-markdown PDFs + `FULL-REPORT.pdf`

**Add `--strict` to treat warnings as critical** (useful in CI / scripted pipelines).

**The QA pass does not auto-fix issues.** It reports them. Operator decides: fix or accept (warnings) / fix-required (criticals).

If you bypass QA and ship with criticals, future audits inherit the consistency-degradation problem the rules exist to prevent.

---

## 7. Versioning

Tools and process docs change. When updating:

| File | Bump when |
|---|---|
| `tools/discover.py` `SCRIPT_VERSION` | Schema validation rules change, new checks added, output format changes, PSI metric set changes |
| `tools/qa.py` `SCRIPT_VERSION` | New QA checks added, severity thresholds changed |
| `tools/AUDIT-PROCESS.md` | Pipeline phase changes, hard rules change, file structure changes |
| `tools/md_to_pdf.py` `DEFAULT_REPORT_FILES` | Standard deliverables list changes |

Project bins are immutable historical records — once shipped, do not retroactively edit them to reflect new tool versions. Future bins use the new tool; past bins document state-of-the-process at their date.
