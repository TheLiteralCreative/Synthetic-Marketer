"""Prompt templates for the audit pipeline.

Each template targets a specific phase/role. They're parameterized at runtime
with the digest content + business context. Kept in a single file so the
prompts are easy to read, diff, and iterate on. (Future: split per phase
once any individual prompt grows beyond ~100 lines.)
"""
from __future__ import annotations

from textwrap import dedent

# ----------------------------------------------------------------------------
# Phase 2 — five parallel audit subagents
# ----------------------------------------------------------------------------

_OUTPUT_BLOCK = dedent("""\
    Output format — return ONE markdown block:

    ```
    ## {section_title}
    ### Score: X/100
    ### Key Finding (one line)
    ### What's Working
    - bullet
    ### What's Broken
    - bullet (Critical / High / Medium / Low severity)
    ### Quick Wins (1-week)
    1. action
    ### Strategic Recommendations (1-3 month)
    1. action
    ```

    Be specific. Quote exact text from the site where relevant. Score 0–100
    where ≤40 is Critical, 41–55 is Below Average, 56–69 is Adequate,
    70–84 is Strong, 85+ is Excellent. Return only the markdown block.
""")


SUBAGENT_BRIEFS = {
    "content": dedent("""\
        You are the Content & Messaging analyst for a marketing audit of {url}.

        Read the discovery digest below — it contains the full site map,
        observed strengths/weaknesses, products, audiences, and content surfaces.

        Your scope (Content & Messaging only):
        1. Headline / hero clarity — does the homepage hero pass the 5-second test?
        2. Value proposition strength — for each audience segment, is the value clear?
        3. Body copy quality — does it speak to actual pains in concrete terms?
        4. Social proof presence and quality (testimonials, reviews, case studies)
        5. Content depth / authority (blog, resources, guides)
        6. Brand voice consistency across pages
        7. Specific language wins/misses — quote 3-5 phrases that work and 3-5 that should be rewritten

        DIGEST:
        {digest}
    """) + "\n" + _OUTPUT_BLOCK.format(section_title="Content & Messaging Analysis"),

    "conversion": dedent("""\
        You are the Conversion Optimization analyst for a marketing audit of {url}.

        Read the discovery digest below for full CTA inventory, form structure,
        and conversion surfaces.

        Your scope (Conversion only):
        1. CTA effectiveness — quality, placement, contrast, urgency
        2. Form analysis — fields, segmentation, friction
        3. Funnel design — TOFU / MOFU / BOFU surface coverage
        4. Trust signals at conversion points
        5. Mobile experience implied from HTML structure
        6. Pricing transparency relative to category norms
        7. Specific friction points and rank-ordered fixes

        DIGEST:
        {digest}
    """) + "\n" + _OUTPUT_BLOCK.format(section_title="Conversion Optimization Analysis"),

    "seo": dedent("""\
        You are the SEO & Technical analyst for a marketing audit of {url}.

        The discovery digest already contains: schema findings, robots.txt analysis,
        title/meta inventory, H-tag audit, image alt coverage, sitemap data,
        and (when available) Core Web Vitals from PageSpeed Insights.

        Your scope (SEO & technical only):
        1. On-page SEO — titles, metas, H-tag hierarchy, image alt, internal linking
        2. Schema markup gaps and defects (the digest already lists these — assess severity)
        3. Content / keyword strategy given the site's structure
        4. AI search visibility (GEO) — robots.txt AI-crawler block status, llms.txt
        5. Technical hygiene — Core Web Vitals if PSI ran, page weight, mobile
        6. Local SEO if applicable (NAP consistency)
        7. Specific quick wins vs. strategic SEO investments

        DIGEST:
        {digest}
    """) + "\n" + _OUTPUT_BLOCK.format(section_title="SEO & Discoverability Analysis"),

    "competitive": dedent("""\
        You are the Competitive Positioning analyst for a marketing audit of {url}.

        Read the discovery digest below to understand the business and its claimed
        positioning. Use your domain knowledge to identify likely competitors
        (the digest doesn't list competitors — that comes from your reasoning
        about the business type and category).

        Your scope (Competitive Positioning only):
        1. Unique positioning clarity — what does the brand claim to be?
        2. Defensible differentiators vs. table-stakes claims
        3. Likely competitive set — identify 3-5 plausible competitors
        4. Comparison opportunities (/vs/ pages, comparison content)
        5. Strategic position recommendation — sharpest credible position

        DIGEST:
        {digest}
    """) + "\n" + _OUTPUT_BLOCK.format(section_title="Competitive Positioning Analysis"),

    "brand_growth": dedent("""\
        You are the Brand, Trust & Growth Strategy analyst for a marketing audit of {url}.

        You produce TWO scores in one report — Brand & Trust (10% weight) and
        Growth & Strategy (10% weight).

        Brand & Trust scope:
        1. Design quality and visual polish
        2. Trust signals depth (reviews, named team, certifications)
        3. Authority indicators
        4. Brand voice consistency
        5. The "human face" gap (named team, faces, bios)

        Growth & Strategy scope:
        1. Business model clarity
        2. Pricing strategy
        3. Growth loops — referral, content, email nurture, community
        4. Retention signals
        5. Channel mix and acquisition

        DIGEST:
        {digest}

        Output format — return ONE markdown block with TWO sections:

        ```
        ## Brand & Trust Analysis
        ### Score: X/100
        ### Key Finding (one line)
        ### Trust Stack (What's There)
        - bullet
        ### Trust Stack (What's Missing)
        - bullet (severity)
        ### Quick Wins (1-week)
        1. action
        ### Strategic Recommendations (1-3 month)
        1. action

        ## Growth & Strategy Analysis
        ### Score: X/100
        ### Key Finding (one line)
        ### Growth Loops Audit
        | Loop | Status | Strength |
        |---|---|---|
        ### Channel Mix Assessment
        | Channel | Strength | Recommendation |
        |---|---|---|
        ### Quick Wins (1-week)
        1. action
        ### Strategic Recommendations (1-3 month)
        1. action
        ```

        Return only the two markdown blocks above (concatenated).
    """),
}


# ----------------------------------------------------------------------------
# Phase 3 — aggregate audit (MARKETING-AUDIT.md)
# ----------------------------------------------------------------------------

AGGREGATE_AUDIT = dedent("""\
    You are aggregating the outputs of 5 parallel audit subagents into a single
    cohesive MARKETING-AUDIT.md file for {url}.

    The six categories and weights:
    - Content & Messaging — 25%
    - Conversion Optimization — 20%
    - SEO & Discoverability — 20%
    - Competitive Positioning — 15%
    - Brand & Trust — 10%
    - Growth & Strategy — 10%

    Compute the composite score (rounded to integer) using the per-category
    scores below. Grade scale: 85+ A, 70–84 B, 55–69 C, 40–54 D, <40 F.

    SUBAGENT OUTPUTS:
    {subagent_outputs}

    DISCOVERY DIGEST (for context — do not reproduce):
    {digest}

    Produce a complete MARKETING-AUDIT.md with these sections in order:

    1. Header (URL, date, business type, overall score + grade)
    2. Executive Summary (3–5 paragraphs, mention top findings + estimated revenue impact)
    3. Score Breakdown (full 6-row table with weighted scores)
    4. Quick Wins (This Week) — numbered list 8–12 items with impact ratings
    5. Strategic Recommendations (1–3 Months) — numbered list 6–10 items
    6. Long-Term Initiatives (3–6 Months) — numbered list 4–7 items
    7. Detailed Analysis by Category — incorporate each subagent's findings
    8. Revenue Impact Summary table
    9. Next Steps — 3 prioritized action items

    Voice rules (HARD):
    - No cross-audit references. This audit must read as self-contained. NEVER
      mention "previous audits", "this engagement", "across all audits", or
      reference any other brand by name unless that brand is a competitor or
      market context.
    - Direct, specific, opinionated. Quote exact site copy where relevant.

    Return ONLY the markdown content — no preamble, no commentary.
""")


# ----------------------------------------------------------------------------
# Phase 4 — companion reports
# ----------------------------------------------------------------------------

COMPETITOR_REPORT = dedent("""\
    You are writing COMPETITOR-REPORT.md — a deep competitive intelligence report
    for {url}.

    AUDIT CONTEXT:
    {audit_excerpt}

    Produce a complete competitor report with these sections:
    1. Executive Summary — 3-4 paragraphs on the competitive landscape
    2. Market Map — segment competitors into tiers
    3. Profiles of 4-8 competitors (most relevant first), each with:
       - Positioning headline
       - Target customer
       - Pricing posture
       - Social proof depth
       - Content/SEO posture
       - Key differentiators
       - Weaknesses
       - "How {brand} wins/loses against them"
    4. Comparison Matrix — table covering Headline Clarity, Value Prop, Trust
       Signals, CTA Effectiveness, Pricing Clarity, Content Depth (1-10 scale)
    5. Strategic Recommendations — 5-7 prioritized recommendations specifically
       about competitive positioning
    6. Sources — list URLs / inputs you used

    Voice rules (HARD): no cross-audit references. Self-contained doc.

    Return ONLY the markdown content.
""")


AUDIENCE_REPORT = dedent("""\
    You are writing ADS-AUDIENCE.md — an audience persona / ICP report for {url}.

    AUDIT CONTEXT:
    {audit_excerpt}

    Produce a complete audience report with:
    1. Executive Summary — primary, secondary, cross-sell, deprioritize segments
    2. 5–7 detailed personas. For each:
       - Name + Quick Snapshot
       - Demographics (age, location, income)
       - Firmographics if applicable
       - Psychographics (values, fears, aspirations)
       - Pain Points (in their voice)
       - Buying Triggers
       - Objections
       - Decision Process
       - Preferred Channels
       - Meta/Google/LinkedIn ad targeting parameters
       - Persona Score for this brand (1-10) with justification
    3. Negative Audiences — who NOT to target
    4. Channel Allocation Recommendation — percentage split across paid channels
    5. Creative Hooks per Persona — 2-3 ad hook variations per top persona

    Voice rules (HARD): no cross-audit references. Self-contained doc.

    Return ONLY the markdown content.
""")


# ----------------------------------------------------------------------------
# Phase 5 — standard companion deliverables
# ----------------------------------------------------------------------------

EXECUTIVE_BRIEF = dedent("""\
    Write EXECUTIVE-BRIEF.md — a one-page TL;DR distilled from the full audit.

    AUDIT (full text):
    {audit_text}

    Structure (mirror this exactly):
    - Header: URL, date, score, estimated revenue impact
    - "The verdict in one line" (one sentence)
    - "What's actually happening" (one paragraph)
    - "The 5 findings that actually matter" (numbered, ~3 sentences each)
    - "The 5 actions to take this week"
    - "What to do this month"
    - "What to do this quarter"
    - "The single most important thing"
    - "Companion materials" (linking to MARKETING-AUDIT.md, COMPETITOR-REPORT.md,
      ADS-AUDIENCE.md, IMPLEMENTATION-ROADMAP.md, GLOSSARY.md, WALKTHROUGH.md)

    Voice rules (HARD): no cross-audit references. Tight. Specific.

    Return ONLY the markdown content.
""")


WALKTHROUGH = dedent("""\
    Write WALKTHROUGH.md — a narrated tour of the audit.

    AUDIT (full text):
    {audit_text}

    Structure:
    - Header
    - "What [brand] actually is" (paragraph orienting the reader)
    - "What the score actually means" (interpret the score, the band, what's
      keeping it from being lower or higher)
    - "The six categories — what landed where, and why" (table)
    - "The five findings that actually matter" (the same as the audit but
      narrated more conversationally)
    - "What surprises in here are worth flagging" (non-obvious observations)
    - "What the recommendations actually amount to" (group into 2-3 jobs)
    - "Three opinions worth pushing harder" (sharper takes than the audit hedges)
    - "Where to go from here" (links to other deliverables)

    Voice rules (HARD): no cross-audit references. Conversational but specific.
    Opinionated.

    Return ONLY the markdown content.
""")


IMPLEMENTATION_ROADMAP = dedent("""\
    Write IMPLEMENTATION-ROADMAP.md — a 90-day execution plan.

    AUDIT (full text):
    {audit_text}

    Structure:
    - Header (source audit URL, plan horizon, target outcome)
    - "How to read this document" (effort × impact scale, owner column)
    - 4 phase tables, each with task / Effort (1-3) / Impact (1-3) / Owner:
      - Phase 1 — Quick fixes (Week 1)
      - Phase 2 — Foundation building (Weeks 2-4)
      - Phase 3 — Content engine + lead capture (Month 2)
      - Phase 4 — Competitive positioning + scale (Month 3)
    - "Success criteria (90-day endpoint)" — measurable targets table
    - "Sequencing logic — why this order" (1-2 paragraphs)
    - "Risks and watchpoints" (bulleted)
    - "Companion materials" (links)

    Voice rules (HARD): no cross-audit references. Concrete actions, not vague
    advice.

    Return ONLY the markdown content.
""")


GLOSSARY = dedent("""\
    Write GLOSSARY.md — a terminology reference for everything in this audit.

    AUDIT EXCERPT (for context):
    {audit_excerpt}

    Group terms by category. Suggested groups (adjust based on what's in the audit):
    - Industry-specific terms
    - Companies named in the audit (if any competitors were profiled)
    - Marketing & funnel terms (CTA, ICP, BOFU/MOFU/TOFU, lead magnet, etc.)
    - SEO, schema, AI search (schema types, GEO, robots.txt, etc.)
    - Channels and ad targeting

    Each entry: term in bold, then 2-4 sentences. Where a term has audit-specific
    context, note it.

    Voice rules (HARD): no cross-audit references. Calibrate definitions to
    THIS audit's context.

    Return ONLY the markdown content.
""")
