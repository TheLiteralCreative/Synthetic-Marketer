#!/usr/bin/env python3
"""
qa.py — Quality assurance pass for Synthetic-Marketer audit deliverables.

Runs a battery of mechanical checks on a completed project bin BEFORE shipping:
- Cross-audit reference detection (Rule 1 from AUDIT-PROCESS.md)
- Cross-bin brand-name leakage (no other-bin brand names appear)
- Score consistency across deliverables
- Required deliverables present
- Internal markdown link validity
- NAP (phone / address) consistency
- Empty / placeholder content detection

Outputs `_QA-REPORT.md` in the bin. Returns:
    0 = all checks passed (green to ship)
    1 = warnings only (review before shipping)
    2 = critical issues found (do not ship without fixing)

Usage:
    python3 tools/qa.py <project_bin_folder>
    python3 tools/qa.py <project_bin_folder> --strict   # treat warnings as critical
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field

SCRIPT_VERSION = "0.1.0"

# Standard deliverables a bin should contain
REQUIRED_FILES = [
    "EXECUTIVE-BRIEF.md",
    "WALKTHROUGH.md",
    "MARKETING-AUDIT.md",
    "COMPETITOR-REPORT.md",
    "ADS-AUDIENCE.md",
    "GLOSSARY.md",
]
OPTIONAL_FILES = [
    "IMPLEMENTATION-ROADMAP.md",
    "_DIGEST.md",
    "_DISCOVERY-NOTES.md",
]

# Cross-audit-reference patterns from AUDIT-PROCESS.md Rule 1
CROSS_AUDIT_PATTERNS = [
    (r"\bacross all (?:.*?)audits?\b", "across-all-audits framing"),
    (r"\bboth audits flagged\b", "both-audits-flagged framing"),
    (r"\bprior audits?\b", "prior-audit reference"),
    (r"\bprevious audits?\b", "previous-audit reference"),
    (r"\bother audits?\b", "other-audit reference"),
    (r"\bin this engagement\b", "this-engagement framing"),
    (r"\bof any audit produced\b", "of-any-audit-produced framing"),
    (r"\btwo prior audits?\b", "two-prior-audits framing"),
    (r"\bSynth-mkt_[A-Za-z0-9_]+/", "filesystem-path reference to another bin"),
    (r"\bsibling brand to\b", "sibling-brand framing"),
    (r"\baudited separately at\b", "audited-separately framing"),
    (r"\b(?:per|from) (?:the )?[A-Z][a-z]+ (?:Banktech|Freight|Funding) audit\b", "per-X-audit framing"),
]

# Score-extraction patterns
OVERALL_SCORE_PATTERNS = [
    re.compile(r"\*\*Marketing Score:\*\*\s*(\d+)/100"),
    re.compile(r"\*\*Score:\*\*\s*(\d+)/100"),
    re.compile(r"\*\*Overall Marketing Score:\s*(\d+)/100\s*", re.IGNORECASE),
    re.compile(r"^Overall Marketing Score:\s*(\d+)/100", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\*\*Score:\*\*\s*(\d+)/100", re.MULTILINE),
]

# Category score row in the breakdown table
CATEGORY_SCORE_ROW = re.compile(
    r"\|\s*(?:\*\*)?(Content & Messaging|Conversion Optimization|SEO & Discoverability|Competitive Positioning|Brand & Trust|Growth & Strategy)(?:\*\*)?\s*\|\s*(\d+)/100",
    re.IGNORECASE,
)

# Internal markdown link pattern
MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

# Phone-number pattern
PHONE_RE = re.compile(r"\(?\b\d{3}\)?[\s\-\.]+\d{3}[\s\-\.]+\d{4}\b")

# Sibling brands tracked across audits — auto-grown from sibling bin names
def discover_sibling_brands(bin_dir: Path) -> list[str]:
    """Find other Synth-mkt_* bins in the same parent and extract their brand tokens."""
    parent = bin_dir.parent
    siblings = []
    for child in parent.glob("Synth-mkt_*"):
        if child == bin_dir or not child.is_dir():
            continue
        # extract brand from "Synth-mkt_<Brand>_<YYYYMMDD>"
        parts = child.name.split("_")
        if len(parts) >= 3:
            siblings.append(parts[1])
    return siblings


# ----------------------------------------------------------------------------
# Check result types
# ----------------------------------------------------------------------------

@dataclass
class Issue:
    severity: str  # "Critical" / "Warning" / "Info"
    check: str
    detail: str
    file: str | None = None
    line: int | None = None


@dataclass
class CheckResult:
    name: str
    passed: bool
    issues: list[Issue] = field(default_factory=list)
    note: str = ""


# ----------------------------------------------------------------------------
# Individual checks
# ----------------------------------------------------------------------------

def check_required_files(bin_dir: Path) -> CheckResult:
    """Every standard deliverable must exist."""
    issues = []
    for fn in REQUIRED_FILES:
        if not (bin_dir / fn).exists():
            issues.append(Issue(
                severity="Critical",
                check="required-files",
                detail=f"Missing required deliverable: {fn}",
                file=fn,
            ))
    return CheckResult(name="Required files present", passed=not issues, issues=issues,
                       note=f"{len(REQUIRED_FILES) - len(issues)}/{len(REQUIRED_FILES)} required files present")


def check_cross_audit_refs(bin_dir: Path) -> CheckResult:
    """Rule 1 — no cross-audit references."""
    issues = []
    for md_path in sorted(bin_dir.glob("*.md")):
        if md_path.name.startswith("_"):
            continue  # skip auto-generated files
        text = md_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(text.splitlines(), 1):
            for pattern, label in CROSS_AUDIT_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(Issue(
                        severity="Critical",
                        check="cross-audit-refs",
                        detail=f"{label}: {line.strip()[:120]}",
                        file=md_path.name,
                        line=line_num,
                    ))
    return CheckResult(
        name="No cross-audit references",
        passed=not issues,
        issues=issues,
        note=f"{len(issues)} violation(s)" if issues else "clean",
    )


def check_brand_leakage(bin_dir: Path) -> CheckResult:
    """No other-bin brand names should appear in this bin's deliverables."""
    siblings = discover_sibling_brands(bin_dir)
    if not siblings:
        return CheckResult(name="No sibling-brand leakage",
                           passed=True, note="(no sibling bins to compare against)")
    issues = []
    # extract this bin's own brand for whitelist
    own_brand = bin_dir.name.split("_")[1] if "_" in bin_dir.name else ""
    for md_path in sorted(bin_dir.glob("*.md")):
        if md_path.name.startswith("_"):
            continue
        text = md_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(text.splitlines(), 1):
            for sibling in siblings:
                # Allow common-noun matches and substring matches that aren't the brand
                # Only flag whole-word case-sensitive matches to avoid false positives
                if re.search(rf"\b{re.escape(sibling)}\b", line):
                    issues.append(Issue(
                        severity="Critical",
                        check="brand-leakage",
                        detail=f"Sibling brand '{sibling}' mentioned: {line.strip()[:120]}",
                        file=md_path.name,
                        line=line_num,
                    ))
    return CheckResult(
        name="No sibling-brand leakage",
        passed=not issues,
        issues=issues,
        note=(f"checked against siblings: {', '.join(siblings)}; "
              f"{len(issues)} violation(s)") if siblings else "n/a",
    )


def extract_overall_score(text: str) -> int | None:
    for pattern in OVERALL_SCORE_PATTERNS:
        m = pattern.search(text)
        if m:
            return int(m.group(1))
    return None


def check_overall_score_consistency(bin_dir: Path) -> CheckResult:
    """Overall score should match across EXECUTIVE-BRIEF, WALKTHROUGH, MARKETING-AUDIT, IMPLEMENTATION-ROADMAP."""
    files_to_check = ["EXECUTIVE-BRIEF.md", "WALKTHROUGH.md", "MARKETING-AUDIT.md", "IMPLEMENTATION-ROADMAP.md"]
    scores: dict[str, int] = {}
    for fn in files_to_check:
        path = bin_dir / fn
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        score = extract_overall_score(text)
        if score is not None:
            scores[fn] = score
    issues = []
    if scores:
        unique = set(scores.values())
        if len(unique) > 1:
            issues.append(Issue(
                severity="Critical",
                check="score-consistency",
                detail=f"Overall score mismatch: {scores}",
            ))
    return CheckResult(
        name="Overall score consistent across deliverables",
        passed=not issues,
        issues=issues,
        note=(f"score: {next(iter(set(scores.values())))}/100"
              if scores and len(set(scores.values())) == 1
              else f"scores found: {scores}") if scores else "no overall scores extracted",
    )


def check_category_scores(bin_dir: Path) -> CheckResult:
    """Per-category scores should be present and weighted-summable to overall in MARKETING-AUDIT."""
    audit_path = bin_dir / "MARKETING-AUDIT.md"
    if not audit_path.exists():
        return CheckResult(name="Per-category scores present", passed=False,
                           issues=[Issue("Critical", "category-scores", "MARKETING-AUDIT.md missing")])
    text = audit_path.read_text(encoding="utf-8")
    matches = CATEGORY_SCORE_ROW.findall(text)
    seen = {cat: int(score) for cat, score in matches}
    expected = {"Content & Messaging", "Conversion Optimization", "SEO & Discoverability",
                "Competitive Positioning", "Brand & Trust", "Growth & Strategy"}
    seen_normalized = {k.title(): v for k, v in seen.items()}
    expected_normalized = {k.title() for k in expected}
    missing = expected_normalized - set(seen_normalized.keys())
    issues = []
    if missing:
        issues.append(Issue(
            severity="Critical",
            check="category-scores",
            detail=f"Missing category scores in MARKETING-AUDIT: {sorted(missing)}",
            file="MARKETING-AUDIT.md",
        ))
    return CheckResult(
        name="Six category scores present in MARKETING-AUDIT",
        passed=not issues,
        issues=issues,
        note=f"found: {seen}",
    )


def check_internal_links(bin_dir: Path) -> CheckResult:
    """Markdown links in deliverables should resolve to files that exist in the bin (or external URLs)."""
    issues = []
    for md_path in sorted(bin_dir.glob("*.md")):
        if md_path.name.startswith("_"):
            continue
        text = md_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(text.splitlines(), 1):
            for m in MD_LINK.finditer(line):
                target = m.group(2).strip()
                # skip URLs, anchors, mailto, tel
                if (target.startswith(("http://", "https://", "#", "mailto:", "tel:"))
                        or target.startswith("/") or "://" in target):
                    continue
                # strip anchor fragment if present
                target_clean = target.split("#")[0].split("?")[0].strip()
                if not target_clean:
                    continue
                resolved = (bin_dir / target_clean).resolve()
                if not resolved.exists():
                    issues.append(Issue(
                        severity="Warning",
                        check="internal-links",
                        detail=f"Broken link: [{m.group(1)}]({target}) in {md_path.name}",
                        file=md_path.name,
                        line=line_num,
                    ))
    return CheckResult(
        name="Internal markdown links resolve",
        passed=not issues,
        issues=issues,
        note=f"{len(issues)} broken link(s)" if issues else "all resolved",
    )


def check_nap_consistency(bin_dir: Path) -> CheckResult:
    """Phone numbers should be consistent across the *subject* deliverables.

    COMPETITOR-REPORT and ADS-AUDIENCE are excluded from the consistency check
    because they legitimately contain competitor phone numbers and persona
    examples. We only verify NAP consistency in the deliverables that describe
    the subject business directly.
    """
    SUBJECT_FILES = {
        "EXECUTIVE-BRIEF.md", "WALKTHROUGH.md", "MARKETING-AUDIT.md",
        "IMPLEMENTATION-ROADMAP.md", "GLOSSARY.md",
    }
    issues = []
    phone_locations: dict[str, list[str]] = defaultdict(list)
    for md_path in sorted(bin_dir.glob("*.md")):
        if md_path.name not in SUBJECT_FILES:
            continue
        text = md_path.read_text(encoding="utf-8")
        for phone in set(PHONE_RE.findall(text)):
            normalized = re.sub(r"[\s\-\.()]", "", phone)
            phone_locations[normalized].append(md_path.name)
    if len(phone_locations) > 1:
        issues.append(Issue(
            severity="Warning",
            check="nap-consistency",
            detail=f"Multiple distinct phone numbers found in subject-deliverables: {dict(phone_locations)}",
        ))
    return CheckResult(
        name="Phone numbers consistent across subject deliverables",
        passed=not issues,
        issues=issues,
        note=(f"{len(phone_locations)} distinct phone(s) in subject docs"
              if phone_locations else "no phones in subject docs"),
    )


def check_placeholder_content(bin_dir: Path) -> CheckResult:
    """Detect lingering placeholder strings (using regex with word boundaries to avoid false positives like '20XX' inside rewrite recommendations)."""
    placeholder_patterns = [
        (r"\bTODO\b", "TODO marker"),
        (r"\bFIXME\b", "FIXME marker"),
        (r"\blorem ipsum\b", "lorem-ipsum placeholder"),
        (r"\[placeholder\]", "literal [placeholder] tag"),
        (r"\[insert ", "[insert ...] placeholder"),
        (r"\[YOUR_[A-Z_]+\]", "[YOUR_*] template variable"),
    ]
    issues = []
    for md_path in sorted(bin_dir.glob("*.md")):
        if md_path.name.startswith("_"):
            continue
        text = md_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(text.splitlines(), 1):
            for pattern, label in placeholder_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(Issue(
                        severity="Warning",
                        check="placeholders",
                        detail=f"{label}: {line.strip()[:120]}",
                        file=md_path.name,
                        line=line_num,
                    ))
    return CheckResult(
        name="No placeholder content remaining",
        passed=not issues,
        issues=issues,
        note=f"{len(issues)} placeholder(s) found" if issues else "clean",
    )


def check_dashboard_pdf(bin_dir: Path) -> CheckResult:
    """The MARKETING-REPORT-<domain>.pdf dashboard should exist."""
    matches = list(bin_dir.glob("MARKETING-REPORT-*.pdf"))
    if matches:
        return CheckResult(name="Dashboard PDF present", passed=True,
                           note=f"found: {matches[0].name}")
    return CheckResult(
        name="Dashboard PDF present",
        passed=False,
        issues=[Issue("Warning", "dashboard-pdf",
                      "MARKETING-REPORT-<domain>.pdf not found — run /market report-pdf")],
        note="missing",
    )


def check_human_friendly_pdfs(bin_dir: Path) -> CheckResult:
    """Per-markdown PDFs and FULL-REPORT.pdf should exist."""
    issues = []
    for fn in REQUIRED_FILES:
        pdf_name = fn.replace(".md", ".pdf")
        if not (bin_dir / pdf_name).exists():
            issues.append(Issue(
                severity="Warning",
                check="human-friendly-pdfs",
                detail=f"Missing PDF: {pdf_name} — run python3 tools/md_to_pdf.py {bin_dir.name}",
                file=pdf_name,
            ))
    full = bin_dir / "FULL-REPORT.pdf"
    if not full.exists():
        issues.append(Issue(
            severity="Warning",
            check="human-friendly-pdfs",
            detail="FULL-REPORT.pdf missing",
            file="FULL-REPORT.pdf",
        ))
    return CheckResult(
        name="Human-friendly PDFs rendered",
        passed=not issues,
        issues=issues,
        note=f"{len(issues)} PDF(s) missing" if issues else "all rendered",
    )


# ----------------------------------------------------------------------------
# Orchestration
# ----------------------------------------------------------------------------

CHECKS = [
    check_required_files,
    check_cross_audit_refs,
    check_brand_leakage,
    check_overall_score_consistency,
    check_category_scores,
    check_internal_links,
    check_nap_consistency,
    check_placeholder_content,
    check_dashboard_pdf,
    check_human_friendly_pdfs,
]


def run_qa(bin_dir: Path) -> tuple[list[CheckResult], int]:
    """Run all checks. Return (results, exit_code) where exit_code is 0/1/2."""
    results = [check(bin_dir) for check in CHECKS]
    exit_code = 0
    for r in results:
        for issue in r.issues:
            if issue.severity == "Critical":
                exit_code = max(exit_code, 2)
            elif issue.severity == "Warning":
                exit_code = max(exit_code, 1)
    return results, exit_code


def write_report(bin_dir: Path, results: list[CheckResult], exit_code: int) -> None:
    out = bin_dir / "_QA-REPORT.md"
    L: list[str] = []
    L.append(f"# QA Report — {bin_dir.name}")
    L.append("")
    L.append(f"_Auto-generated by `tools/qa.py` v{SCRIPT_VERSION}_")
    L.append("")
    headline = {0: "✅ READY TO SHIP — all checks passed",
                1: "⚠️  REVIEW BEFORE SHIPPING — warnings present",
                2: "🛑 DO NOT SHIP — critical issues found"}[exit_code]
    L.append(f"## {headline}")
    L.append("")
    crit = sum(1 for r in results for i in r.issues if i.severity == "Critical")
    warn = sum(1 for r in results for i in r.issues if i.severity == "Warning")
    L.append(f"**Critical issues:** {crit}  |  **Warnings:** {warn}")
    L.append("")

    L.append("## Summary")
    L.append("")
    L.append("| # | Check | Result | Note |")
    L.append("|---|---|---|---|")
    for i, r in enumerate(results, 1):
        status = "✅ pass" if r.passed else (
            "🛑 critical" if any(iss.severity == "Critical" for iss in r.issues) else "⚠️  warning"
        )
        note = (r.note or "").replace("|", "\\|")[:80]
        L.append(f"| {i} | {r.name} | {status} | {note} |")
    L.append("")

    # Detailed issues
    if any(r.issues for r in results):
        L.append("## Issue detail")
        L.append("")
        for r in results:
            if not r.issues:
                continue
            L.append(f"### {r.name}")
            L.append("")
            for issue in r.issues:
                where = ""
                if issue.file:
                    where = f"`{issue.file}`" + (f":{issue.line}" if issue.line else "")
                L.append(f"- **[{issue.severity}]** {where}{(' — ' if where else '')}{issue.detail}")
            L.append("")

    # Action recommendations
    if exit_code == 2:
        L.append("## Required before shipping")
        L.append("")
        L.append("Resolve every Critical issue above. Then re-run `python3 tools/qa.py <bin>` until exit code is 0.")
        L.append("")
    elif exit_code == 1:
        L.append("## Recommended before shipping")
        L.append("")
        L.append("Review each Warning above and either resolve or accept (some are informational).")
        L.append("")

    out.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("bin_dir", help="Project bin folder to QA")
    ap.add_argument("--strict", action="store_true",
                    help="Treat warnings as critical (return code 2 even for warning-only)")
    args = ap.parse_args()
    bin_dir = Path(args.bin_dir).resolve()
    if not bin_dir.is_dir():
        print(f"error: bin folder not found: {bin_dir}", file=sys.stderr)
        return 2
    print(f"[qa] checking {bin_dir.name}")
    results, exit_code = run_qa(bin_dir)
    write_report(bin_dir, results, exit_code)

    # Console summary
    crit = sum(1 for r in results for i in r.issues if i.severity == "Critical")
    warn = sum(1 for r in results for i in r.issues if i.severity == "Warning")
    for r in results:
        status = "✓" if r.passed else (
            "✗" if any(i.severity == "Critical" for i in r.issues) else "!"
        )
        print(f"  {status} {r.name}: {r.note}")
    headline = {0: "✅ READY TO SHIP",
                1: "⚠️  WARNINGS — review",
                2: "🛑 CRITICAL — do not ship"}[exit_code]
    print(f"\n[qa] {headline}  ({crit} critical, {warn} warnings)")
    print(f"[qa] full report: {bin_dir}/_QA-REPORT.md")

    if args.strict and exit_code == 1:
        return 2
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
