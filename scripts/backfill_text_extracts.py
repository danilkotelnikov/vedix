#!/usr/bin/env python3
"""Backfill pdfminer text extracts for any corpus PDFs missing a sibling .txt.

When a scrape subagent's bash job is killed before the extraction stage
runs (Stage 3 of scrape_oa.py / scrape_scihub.py), the PDFs land on disk
but the matching ``text/<doi-stem>.txt`` is never written. This script
walks the corpus and runs pdfminer.six on any PDF whose .txt is missing
or empty, regardless of which scrape session deposited it.

Idempotent: a PDF whose .txt already exists and is non-empty is skipped.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path


def _corpus_root() -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".")
    return home / ".vedix" / "corpus"


def backfill_discipline(
    discipline: str, lang: str, *, dry_run: bool, log: logging.Logger,
) -> tuple[int, int, int]:
    """Walk ``<corpus>/<discipline>/<lang>/pdf/*.pdf``; extract any missing
    siblings into ``../text/<stem>.txt``.

    Returns ``(scanned, extracted, failed)``.
    """
    pdf_dir = _corpus_root() / discipline / lang / "pdf"
    text_dir = _corpus_root() / discipline / lang / "text"
    if not pdf_dir.exists():
        log.warning("no pdf dir at %s; skipping", pdf_dir)
        return 0, 0, 0
    text_dir.mkdir(parents=True, exist_ok=True)

    from pdfminer.high_level import extract_text as pdf_extract_text

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    scanned = len(pdfs)
    extracted = 0
    failed = 0

    for pdf in pdfs:
        txt = text_dir / (pdf.stem + ".txt")
        if txt.exists() and txt.stat().st_size > 0:
            continue
        if dry_run:
            log.info("  [dry] would extract %s", pdf.name)
            extracted += 1
            continue
        t0 = time.time()
        try:
            text = pdf_extract_text(str(pdf))
        except Exception as exc:  # noqa: BLE001
            log.warning("  FAIL %s: %s", pdf.name, exc)
            failed += 1
            continue
        if not text or len(text.strip()) < 100:
            log.warning("  thin extract for %s (%d chars); writing anyway",
                        pdf.name, len(text or ""))
        txt.write_text(text or "", encoding="utf-8")
        dt = time.time() - t0
        log.info("  ok %s -> %d chars (%.1fs)", pdf.name, len(text or ""), dt)
        extracted += 1

    return scanned, extracted, failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--disciplines", nargs="+",
                    default=["biology", "chemistry", "computer_science",
                             "geology", "materials", "medicine", "physics"],
                    help="Disciplines to backfill (default: all 7).")
    ap.add_argument("--lang", default="en", help="Language subdir (default 'en').")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be extracted; don't write.")
    ap.add_argument("-v", "--verbose", action="count", default=0)
    args = ap.parse_args()

    level = logging.INFO if args.verbose >= 1 else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("vedix.backfill")

    grand_scan = grand_extr = grand_fail = 0
    for d in args.disciplines:
        log.info("=== %s ===", d)
        s, e, f = backfill_discipline(d, args.lang, dry_run=args.dry_run, log=log)
        log.info("  %s: scanned=%d extracted=%d failed=%d", d, s, e, f)
        grand_scan += s
        grand_extr += e
        grand_fail += f

    print()
    print("Backfill summary")
    print("-" * 50)
    print(f"  PDFs scanned:        {grand_scan}")
    print(f"  Text files written:  {grand_extr}")
    print(f"  Failures:            {grand_fail}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
