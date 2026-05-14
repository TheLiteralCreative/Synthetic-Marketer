"""Active/Legacy audit-folder layout.

Bins are written to `<output_folder>/Active-Audits/<bin_name>`. When a new
audit runs against a brand that already has a folder in Active-Audits, the
existing folder is demoted to `<output_folder>/Legacy-Audits/<bin_name>_<N>`,
where N is the iteration count for that brand in Legacy-Audits (including
the one being added). Brand matching is case-insensitive.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

ACTIVE_DIRNAME = "Active-Audits"
LEGACY_DIRNAME = "Legacy-Audits"

# Bin name shape: Synth-mkt_<brand>_<YYYYMMDD>[_<N>]
# Brand may contain letters, digits, hyphens. Date is 8 digits. The optional
# trailing _<N> suffix is what we apply when demoting to Legacy.
_BIN_RE = re.compile(r"^Synth-mkt_(?P<brand>.+?)_(?P<date>\d{8})(?:_(?P<iter>\d+))?$")


def active_dir(output_folder: Path) -> Path:
    """Return the Active-Audits path, creating it if missing."""
    p = Path(output_folder) / ACTIVE_DIRNAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def legacy_dir(output_folder: Path, create: bool = False) -> Path:
    """Return the Legacy-Audits path. Only creates it when `create=True`."""
    p = Path(output_folder) / LEGACY_DIRNAME
    if create:
        p.mkdir(parents=True, exist_ok=True)
    return p


def parse_bin_name(name: str) -> tuple[str, str, int | None] | None:
    """Split a bin folder name into (brand, date, iteration). None if invalid."""
    m = _BIN_RE.match(name)
    if not m:
        return None
    it = m.group("iter")
    return m.group("brand"), m.group("date"), (int(it) if it else None)


def _brand_key(brand: str) -> str:
    return brand.casefold()


def find_active_for_brand(output_folder: Path, brand: str) -> Path | None:
    """Return the existing Active-Audits folder matching this brand, if any.

    Brand match is case-insensitive on the brand token only — the date and
    any trailing iteration suffix are ignored.
    """
    adir = Path(output_folder) / ACTIVE_DIRNAME
    if not adir.is_dir():
        return None
    target = _brand_key(brand)
    for child in adir.iterdir():
        if not child.is_dir():
            continue
        parsed = parse_bin_name(child.name)
        if not parsed:
            continue
        if _brand_key(parsed[0]) == target:
            return child
    return None


def count_legacy_for_brand(output_folder: Path, brand: str) -> int:
    """Count Legacy-Audits folders matching this brand (case-insensitive)."""
    ldir = Path(output_folder) / LEGACY_DIRNAME
    if not ldir.is_dir():
        return 0
    target = _brand_key(brand)
    n = 0
    for child in ldir.iterdir():
        if not child.is_dir():
            continue
        parsed = parse_bin_name(child.name)
        if not parsed:
            continue
        if _brand_key(parsed[0]) == target:
            n += 1
    return n


def demote_active_to_legacy(output_folder: Path, brand: str) -> Path | None:
    """If an Active folder exists for this brand, move it to Legacy with
    an `_<N>` suffix appended to the original name. Returns the new path
    in Legacy, or None if there was nothing to demote.

    N = (existing Legacy iterations for this brand) + 1 (the one we're adding).
    """
    existing = find_active_for_brand(output_folder, brand)
    if existing is None:
        return None
    parsed = parse_bin_name(existing.name)
    if not parsed:
        # Shouldn't happen — find_active_for_brand only returns parsed names.
        return None
    base_name = f"Synth-mkt_{parsed[0]}_{parsed[1]}"
    new_iter = count_legacy_for_brand(output_folder, brand) + 1
    ldir = legacy_dir(output_folder, create=True)
    dest = ldir / f"{base_name}_{new_iter}"
    # Defensive: if dest already exists (collision from a manual rename),
    # bump until we find a free slot.
    while dest.exists():
        new_iter += 1
        dest = ldir / f"{base_name}_{new_iter}"
    shutil.move(str(existing), str(dest))
    return dest
