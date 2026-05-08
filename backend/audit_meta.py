"""Parse a project bin to extract audit metadata for the GUI's detail view.

The MARKETING-AUDIT.md file is the source of truth for score, categories,
findings, and recommendations. This module reads it and returns a structured
shape the frontend can render directly.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

CATEGORY_NAMES = [
    "Content & Messaging",
    "Conversion Optimization",
    "SEO & Discoverability",
    "Competitive Positioning",
    "Brand & Trust",
    "Growth & Strategy",
]
CATEGORY_WEIGHTS = {
    "Content & Messaging": 25,
    "Conversion Optimization": 20,
    "SEO & Discoverability": 20,
    "Competitive Positioning": 15,
    "Brand & Trust": 10,
    "Growth & Strategy": 10,
}

# Standard deliverable filenames in display order
STANDARD_DELIVERABLES = [
    ("EXECUTIVE-BRIEF.md", "EXECUTIVE-BRIEF.pdf", "Executive brief", "TL;DR for stakeholders"),
    ("WALKTHROUGH.md", "WALKTHROUGH.pdf", "Walkthrough", "Narrated tour"),
    ("MARKETING-AUDIT.md", "MARKETING-AUDIT.pdf", "Marketing audit", "Full 6-category scorecard"),
    ("COMPETITOR-REPORT.md", "COMPETITOR-REPORT.pdf", "Competitor report", "Competitive intelligence"),
    ("ADS-AUDIENCE.md", "ADS-AUDIENCE.pdf", "Audience report", "Personas + targeting"),
    ("IMPLEMENTATION-ROADMAP.md", "IMPLEMENTATION-ROADMAP.pdf", "Implementation roadmap", "90-day execution plan"),
    ("GLOSSARY.md", "GLOSSARY.pdf", "Glossary", "Audit-specific terminology"),
]


# ----------------------------------------------------------------------------
# Score / category extraction (mirrors tools/qa.py logic)
# ----------------------------------------------------------------------------

OVERALL_SCORE_RE = re.compile(r"\b(\d{1,3})\s*/\s*100\b")

CATEGORY_ROW_RE = re.compile(
    r"\|\s*(?:\*\*)?(Content & Messaging|Conversion Optimization|"
    r"SEO & Discoverability|Competitive Positioning|Brand & Trust|"
    r"Growth & Strategy)(?:\*\*)?\s*\|([^\n]+)",
    re.IGNORECASE,
)


def _row_score(remainder: str) -> int | None:
    cells = [c.strip().lstrip("*").rstrip("*").strip() for c in remainder.split("|")]
    for cell in cells:
        if not cell or cell.endswith("%"):
            continue
        m = re.match(r"^(\d{1,3})(?:\s*/\s*100)?$", cell)
        if m:
            n = int(m.group(1))
            if 0 <= n <= 100:
                return n
    return None


def grade_for(score: int | None) -> str:
    if score is None:
        return "?"
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


# ----------------------------------------------------------------------------
# Findings extraction
# ----------------------------------------------------------------------------

# Two patterns the LLM uses for findings:
# 1. "- ZERO testimonials (Critical)"  — severity in trailing parens
# 2. "**[Critical]** description here"  — severity in leading brackets
TRAILING_SEV_RE = re.compile(
    r"^[-*•]\s+(.+?)\s+\((Critical|High|Medium|Low)\)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
LEADING_SEV_RE = re.compile(
    r"^\s*[-*•]?\s*\**\[(Critical|High|Medium|Low)\]\**\s*[:\-—]?\s*(.+?)(?:\n|$)",
    re.IGNORECASE | re.MULTILINE,
)
# Also: a Severity column in a markdown table — "| Critical | description |"
TABLE_SEV_RE = re.compile(
    r"\|\s*(?:\*\*)?(Critical|High|Medium|Low)(?:\*\*)?\s*\|\s*([^\|]{30,400})\s*\|",
    re.IGNORECASE,
)

SEV_PRIORITY = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

# Section header followed by bullets — common in older audits.
# e.g.,
#   **What's broken (Critical):**
#   - bullet text
#   - bullet text
SECTION_HEADER_RE = re.compile(
    r"\*\*[^*\n]*\((Critical|High|Medium|Low)\)[^*\n]*:?\*\*\s*\n"
    r"((?:[ \t]*[-*•][^\n]+\n?)+)",
    re.IGNORECASE,
)
BULLET_RE = re.compile(r"^[ \t]*[-*•]\s+(.+)$", re.MULTILINE)


def extract_findings(audit_text: str, limit: int = 10) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _add(sev: str, text: str) -> None:
        text = re.sub(r"\s+", " ", text).strip().rstrip(".").strip("*").strip()
        if not (30 < len(text) < 400):
            return
        sev_t = sev.title()
        key = (sev_t, text[:60])
        if key in seen:
            return
        seen.add(key)
        findings.append({"severity": sev_t, "finding": text})

    # Pattern 1: trailing parens — "- text (Critical)"
    for m in TRAILING_SEV_RE.finditer(audit_text):
        _add(m.group(2), m.group(1))

    # Pattern 2: leading bracket/bold — "**[Critical]** text"
    for m in LEADING_SEV_RE.finditer(audit_text):
        _add(m.group(1), m.group(2))

    # Pattern 3: markdown table cell — "| Critical | description |"
    for m in TABLE_SEV_RE.finditer(audit_text):
        _add(m.group(1), m.group(2))

    # Pattern 4: section header + bullets — "**What's broken (Critical):**\n- ..."
    for m in SECTION_HEADER_RE.finditer(audit_text):
        sev = m.group(1)
        bullets_block = m.group(2)
        for bm in BULLET_RE.finditer(bullets_block):
            _add(sev, bm.group(1))

    findings.sort(key=lambda f: SEV_PRIORITY.get(f["severity"], 9))
    return findings[:limit]


# ----------------------------------------------------------------------------
# Top-level parse
# ----------------------------------------------------------------------------

def parse_bin(bin_dir: Path) -> dict[str, Any]:
    """Read a project bin and return structured metadata for the GUI."""
    bin_dir = Path(bin_dir).resolve()
    out: dict[str, Any] = {
        "name": bin_dir.name,
        "path": str(bin_dir),
        "exists": bin_dir.is_dir(),
        "modified": None,
        "score": None,
        "grade": "?",
        "url": None,
        "date": None,
        "business_type": None,
        "categories": [],
        "findings": [],
        "qa": None,
        "deliverables": [],
        "extras": [],
    }
    if not out["exists"]:
        return out
    out["modified"] = bin_dir.stat().st_mtime

    audit_path = bin_dir / "MARKETING-AUDIT.md"
    if audit_path.exists():
        text = audit_path.read_text(encoding="utf-8", errors="replace")
        m = OVERALL_SCORE_RE.search(text)
        if m:
            out["score"] = int(m.group(1))
            out["grade"] = grade_for(out["score"])
        m = re.search(r"\*\*URL:\*\*\s*(\S+)", text)
        if m:
            out["url"] = m.group(1)
        m = re.search(r"\*\*Date:\*\*\s*([^\n]+)", text) or re.search(r"\*\*Audit Date:\*\*\s*([^\n]+)", text)
        if m:
            out["date"] = m.group(1).strip().rstrip(".").strip()
        m = re.search(r"\*\*Business Type:\*\*\s*([^\n]+)", text)
        if m:
            out["business_type"] = m.group(1).strip().rstrip(".").strip()

        # Categories
        cat_scores: dict[str, int] = {}
        for cat_match in CATEGORY_ROW_RE.finditer(text):
            cat = cat_match.group(1)
            if cat in cat_scores:
                continue
            score = _row_score(cat_match.group(2))
            if score is not None:
                cat_scores[cat] = score
        out["categories"] = [
            {"name": n, "score": cat_scores.get(n), "weight": CATEGORY_WEIGHTS[n]}
            for n in CATEGORY_NAMES
        ]

        out["findings"] = extract_findings(text, limit=10)

    # QA report
    qa_path = bin_dir / "_QA-REPORT.md"
    if qa_path.exists():
        qa_text = qa_path.read_text(encoding="utf-8", errors="replace")
        if "READY TO SHIP" in qa_text:
            qa_status = "ready"
        elif "REVIEW BEFORE SHIPPING" in qa_text:
            qa_status = "warnings"
        elif "DO NOT SHIP" in qa_text:
            qa_status = "critical"
        else:
            qa_status = "unknown"
        crit = re.search(r"\*\*Critical issues:\*\*\s*(\d+)", qa_text)
        warn = re.search(r"\*\*Warnings:\*\*\s*(\d+)", qa_text)
        out["qa"] = {
            "status": qa_status,
            "critical": int(crit.group(1)) if crit else 0,
            "warnings": int(warn.group(1)) if warn else 0,
        }

    # Deliverables
    deliverables = []
    for md_name, pdf_name, label, blurb in STANDARD_DELIVERABLES:
        md_path = bin_dir / md_name
        pdf_path = bin_dir / pdf_name
        if md_path.exists() or pdf_path.exists():
            deliverables.append({
                "label": label,
                "blurb": blurb,
                "md": md_name if md_path.exists() else None,
                "pdf": pdf_name if pdf_path.exists() else None,
                "size_kb": (pdf_path.stat().st_size // 1024) if pdf_path.exists() else None,
            })
    out["deliverables"] = deliverables

    # Extras (FULL-REPORT.pdf, MARKETING-REPORT-*.pdf, _DIGEST, _QA-REPORT)
    extras = []
    for child in bin_dir.glob("*"):
        if not child.is_file():
            continue
        name = child.name
        # skip files already enumerated in deliverables
        if any(name == md or name == pdf for md, pdf, *_ in STANDARD_DELIVERABLES):
            continue
        if name.startswith("."):
            continue
        if name == "MARKETING-AUDIT.pdf":  # already in deliverables
            continue
        if name in ("_DIGEST.md", "_DISCOVERY-NOTES.md", "_QA-REPORT.md"):
            extras.append({"name": name, "label": _extra_label(name), "size_kb": child.stat().st_size // 1024})
        elif name.endswith(".pdf") or name.endswith(".md"):
            extras.append({"name": name, "label": _extra_label(name), "size_kb": child.stat().st_size // 1024})
    out["extras"] = extras

    return out


def _extra_label(name: str) -> str:
    if name.startswith("MARKETING-REPORT-"):
        return "Dashboard PDF"
    if name == "FULL-REPORT.pdf":
        return "Full bundled report"
    if name == "_DIGEST.md":
        return "Discovery digest"
    if name == "_DISCOVERY-NOTES.md":
        return "Discovery checklist"
    if name == "_QA-REPORT.md":
        return "QA report"
    return name


# ----------------------------------------------------------------------------
# Bin discovery (for the All Audits list)
# ----------------------------------------------------------------------------

def list_bins(parent: Path) -> list[dict[str, Any]]:
    """Light-touch listing — just enough for the All Audits sortable table.

    Heavy work (categories, findings) is deferred to parse_bin() when the user
    clicks into a specific bin.
    """
    parent = Path(parent).resolve()
    out = []
    if not parent.is_dir():
        return out
    for child in sorted(parent.glob("Synth-mkt_*"), reverse=True):
        if not child.is_dir():
            continue
        info = {
            "name": child.name,
            "path": str(child),
            "modified": child.stat().st_mtime,
            "score": None,
            "grade": "?",
            "qa": None,
            "url": None,
            "date": None,
        }
        # quick parse — score + qa status only
        audit = child / "MARKETING-AUDIT.md"
        if audit.exists():
            text = audit.read_text(encoding="utf-8", errors="replace")
            m = OVERALL_SCORE_RE.search(text)
            if m:
                info["score"] = int(m.group(1))
                info["grade"] = grade_for(info["score"])
            m = re.search(r"\*\*URL:\*\*\s*(\S+)", text)
            if m:
                info["url"] = m.group(1)
            m = re.search(r"\*\*Date:\*\*\s*([^\n]+)", text) or \
                re.search(r"\*\*Audit Date:\*\*\s*([^\n]+)", text)
            if m:
                info["date"] = m.group(1).strip().rstrip(".").strip()
        qa = child / "_QA-REPORT.md"
        if qa.exists():
            qa_text = qa.read_text(encoding="utf-8", errors="replace")
            if "READY TO SHIP" in qa_text:
                info["qa"] = "ready"
            elif "REVIEW BEFORE SHIPPING" in qa_text:
                info["qa"] = "warnings"
            elif "DO NOT SHIP" in qa_text:
                info["qa"] = "critical"
        out.append(info)
    return out
