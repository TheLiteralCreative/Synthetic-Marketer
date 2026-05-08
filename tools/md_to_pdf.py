#!/usr/bin/env python3
"""
md_to_pdf.py — Convert Synthetic-Marketer report markdowns into human-friendly PDFs.

Renders each .md in a project bin to a styled PDF via Python-markdown -> HTML ->
headless Chrome. Also bundles all of them into a single FULL-REPORT.pdf with a
cover page and table of contents.

Usage:
    python3 tools/md_to_pdf.py <project_bin_folder>
    python3 tools/md_to_pdf.py <project_bin_folder> --no-bundle
    python3 tools/md_to_pdf.py <project_bin_folder> --files MARKETING-AUDIT.md COMPETITOR-REPORT.md

Requires:
    pip install --user markdown
    Google Chrome installed at /Applications/Google Chrome.app (macOS)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

CHROME_BIN_CANDIDATES = [
    # macOS
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    # Windows — common install paths
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    # Linux / WSL / anything on PATH
    shutil.which("google-chrome") or "",
    shutil.which("google-chrome-stable") or "",
    shutil.which("chromium") or "",
    shutil.which("chromium-browser") or "",
    shutil.which("microsoft-edge") or "",
    shutil.which("chrome") or "",
]

DEFAULT_REPORT_FILES = [
    "EXECUTIVE-BRIEF.md",
    "WALKTHROUGH.md",
    "MARKETING-AUDIT.md",
    "COMPETITOR-REPORT.md",
    "ADS-AUDIENCE.md",
    "IMPLEMENTATION-ROADMAP.md",
    "GLOSSARY.md",
]

CSS = """
@page {
    size: Letter;
    margin: 0.85in 0.9in 0.95in 0.9in;
}
html { font-size: 14px; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #1f2937;
    line-height: 1.55;
    max-width: 100%;
    margin: 0;
    padding: 0;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}
.cover {
    page-break-after: always;
    text-align: left;
    padding-top: 1.4in;
}
.cover .label {
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
}
.cover h1 {
    font-size: 2.6rem;
    margin: 0 0 0.6rem 0;
    color: #1B2A4A;
    border: none;
    padding: 0;
}
.cover .url {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 1rem;
    color: #2D5BFF;
    word-break: break-all;
}
.cover .meta {
    margin-top: 2rem;
    font-size: 0.95rem;
    color: #4b5563;
}
.cover .toc {
    margin-top: 2.5rem;
}
.cover .toc h2 {
    font-size: 1.05rem;
    color: #1B2A4A;
    border: none;
    padding: 0;
    margin: 0 0 0.6rem 0;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.cover .toc ol {
    padding-left: 1.2rem;
    margin: 0;
}
.cover .toc li {
    margin-bottom: 0.35rem;
}
.section-break {
    page-break-before: always;
}
h1, h2, h3, h4, h5, h6 {
    color: #1B2A4A;
    line-height: 1.25;
    margin-top: 1.6rem;
    margin-bottom: 0.6rem;
}
h1 {
    font-size: 1.85rem;
    border-bottom: 2px solid #1B2A4A;
    padding-bottom: 0.4rem;
    margin-top: 0;
    page-break-before: auto;
}
h2 {
    font-size: 1.35rem;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.25rem;
}
h3 { font-size: 1.1rem; }
h4 { font-size: 1.0rem; color: #374151; }
p { margin: 0.5rem 0 0.7rem 0; }
strong { color: #111827; }
em { color: #374151; }
a { color: #2D5BFF; text-decoration: none; }
hr {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 1.4rem 0;
}
ul, ol {
    padding-left: 1.4rem;
    margin: 0.4rem 0 0.9rem 0;
}
li { margin-bottom: 0.18rem; }
blockquote {
    border-left: 3px solid #cbd5e1;
    padding: 0.1rem 0.9rem;
    color: #4b5563;
    margin: 0.8rem 0;
    background: #f8fafc;
}
code {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.9em;
    background: #f3f4f6;
    padding: 0.08em 0.32em;
    border-radius: 3px;
    color: #1f2937;
}
pre {
    background: #f3f4f6;
    padding: 0.6rem 0.8rem;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 0.85rem;
}
pre code { background: transparent; padding: 0; }
table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.7rem 0 1.1rem 0;
    font-size: 0.92rem;
    page-break-inside: auto;
}
thead { background: #1B2A4A; color: #ffffff; }
thead th {
    text-align: left;
    padding: 0.45rem 0.6rem;
    font-weight: 600;
    border: 1px solid #1B2A4A;
}
tbody td {
    padding: 0.4rem 0.6rem;
    border: 1px solid #e5e7eb;
    vertical-align: top;
}
tbody tr:nth-child(even) td { background: #f8fafc; }
.severity-Critical { color: #DC2626; font-weight: 600; }
.severity-High { color: #EA580C; font-weight: 600; }
.severity-Medium { color: #CA8A04; font-weight: 600; }
.severity-Low { color: #2563EB; font-weight: 600; }
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
{cover}
{body}
</body>
</html>
"""


def find_chrome() -> str:
    # Allow explicit override
    env = os.environ.get("CHROME_BIN")
    if env and Path(env).exists():
        return env
    for cand in CHROME_BIN_CANDIDATES:
        if cand and Path(cand).exists():
            return cand
    raise RuntimeError(
        "Could not find Google Chrome, Chromium, or Edge. "
        "Install one or set CHROME_BIN to a binary path."
    )


def md_to_html(md_text: str) -> str:
    return markdown.markdown(
        md_text,
        extensions=[
            "extra",         # tables, fenced_code, abbr, attr_list, def_list, footnotes
            "sane_lists",
            "smarty",
            "toc",
        ],
        output_format="html5",
    )


def build_cover(title: str, subtitle: str, url: str | None, sections: list[str]) -> str:
    today = dt.date.today().strftime("%B %d, %Y")
    url_html = f'<div class="url">{url}</div>' if url else ""
    toc_html = ""
    if sections:
        items = "\n".join(f"<li>{s}</li>" for s in sections)
        toc_html = f'<div class="toc"><h2>Contents</h2><ol>{items}</ol></div>'
    return f"""
<div class="cover">
    <div class="label">{subtitle}</div>
    <h1>{title}</h1>
    {url_html}
    <div class="meta">Generated {today}</div>
    {toc_html}
</div>
"""


def render_pdf(html: str, out_pdf: Path, chrome_bin: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(html)
        tmp_path = tmp.name
    try:
        cmd = [
            chrome_bin,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--no-sandbox",
            f"--print-to-pdf={out_pdf}",
            f"file://{tmp_path}",
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0 or not out_pdf.exists():
            raise RuntimeError(
                f"Chrome failed (exit {result.returncode})\nstderr: {result.stderr}"
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def render_one(md_path: Path, out_pdf: Path, chrome_bin: str) -> None:
    md_text = md_path.read_text(encoding="utf-8")
    body_html = md_to_html(md_text)
    title = md_path.stem.replace("-", " ").title()
    cover = build_cover(
        title=title,
        subtitle=md_path.stem.replace("-", " "),
        url=None,
        sections=[],
    )
    full_html = HTML_TEMPLATE.format(
        title=title,
        css=CSS,
        cover=cover,
        body=f'<div class="section-break">{body_html}</div>',
    )
    render_pdf(full_html, out_pdf, chrome_bin)


def render_bundle(md_paths: list[Path], out_pdf: Path, chrome_bin: str, label: str) -> None:
    sections = []
    parts = []
    for p in md_paths:
        md_text = p.read_text(encoding="utf-8")
        title = p.stem.replace("-", " ").title()
        sections.append(title)
        body_html = md_to_html(md_text)
        parts.append(f'<div class="section-break">{body_html}</div>')

    cover = build_cover(
        title="Synthetic-Marketer Audit Bundle",
        subtitle=label,
        url=None,
        sections=sections,
    )
    full_html = HTML_TEMPLATE.format(
        title="Synthetic-Marketer Audit Bundle",
        css=CSS,
        cover=cover,
        body="\n".join(parts),
    )
    render_pdf(full_html, out_pdf, chrome_bin)


def detect_target(name: str) -> str:
    """Best-effort label for the bundle cover page (e.g. project bin name)."""
    return name


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("folder", help="Project bin folder containing .md reports")
    ap.add_argument(
        "--files",
        nargs="+",
        default=DEFAULT_REPORT_FILES,
        help="Specific .md filenames to convert (default: the 3 standard reports)",
    )
    ap.add_argument(
        "--no-bundle",
        action="store_true",
        help="Skip generating the bundled FULL-REPORT.pdf",
    )
    ap.add_argument(
        "--bundle-name",
        default="FULL-REPORT.pdf",
        help="Filename for the bundled PDF (default: FULL-REPORT.pdf)",
    )
    args = ap.parse_args()

    folder = Path(args.folder).resolve()
    if not folder.is_dir():
        print(f"error: folder not found: {folder}", file=sys.stderr)
        return 2

    chrome_bin = find_chrome()
    print(f"Chrome:  {chrome_bin}")
    print(f"Folder:  {folder}")

    found = []
    for fn in args.files:
        p = folder / fn
        if p.exists():
            found.append(p)
        else:
            print(f"  skip (not found): {fn}")

    if not found:
        print("error: no input markdown files found", file=sys.stderr)
        return 2

    print(f"Converting {len(found)} markdown file(s) to PDF...")
    for md in found:
        out = folder / f"{md.stem}.pdf"
        render_one(md, out, chrome_bin)
        size_kb = out.stat().st_size / 1024
        print(f"  ✓ {md.name:<28} -> {out.name:<28} ({size_kb:.0f} KB)")

    if not args.no_bundle and len(found) > 1:
        bundle_path = folder / args.bundle_name
        label = detect_target(folder.name)
        render_bundle(found, bundle_path, chrome_bin, label=label)
        size_kb = bundle_path.stat().st_size / 1024
        print(f"  ✓ bundle{'':<22} -> {bundle_path.name:<28} ({size_kb:.0f} KB)")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
