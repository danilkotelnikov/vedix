from __future__ import annotations
import argparse
import os
import shutil
import tarfile
import time
from pathlib import Path
from .kg_store import KGStore, Tier, _palace_root


def verify_command(*, tier: Tier, scope_id: str) -> dict:
    """Walk every paper's claims; assert raw[byte_range] == verbatim_quote."""
    store = KGStore(tier=tier, scope_id=scope_id)
    mismatches: list[dict] = []
    for pid in store.list_paper_ids():
        paper = store.read_paper(pid)
        if paper is None:
            continue
        raw_path = Path(paper.raw_pointer.text)
        if not raw_path.is_absolute():
            raw_path = _job_raw_root(tier=tier, scope_id=scope_id) / raw_path.name
        if not raw_path.exists():
            mismatches.append({"claim_id": "(no_raw)", "paper_id": pid,
                               "reason": f"raw text not found: {raw_path}"})
            continue
        raw = raw_path.read_text(encoding="utf-8")
        for c in paper.nodes.claims:
            s, e = c.quote_byte_range
            actual = raw[s:e]
            if actual != c.verbatim_quote:
                mismatches.append({"claim_id": c.id, "paper_id": pid,
                                   "reason": "verbatim_quote does not match raw byte_range"})
    return {"ok": not mismatches, "mismatches": mismatches}


def rebuild_command(*, tier: Tier, scope_id: str, paper_list_path: Path) -> dict:
    """Wraps GraphBuilder.run() — re-extracts from raw + paper_list.json.
    Preserves user-confirmed lattice merges (read from existing lattice table)."""
    from .graph_builder import GraphBuilder
    import json as _j
    import asyncio
    store = KGStore(tier=tier, scope_id=scope_id)
    paper_list = _j.loads(paper_list_path.read_text(encoding="utf-8"))
    builder = GraphBuilder(store=store)
    return asyncio.run(builder.run(paper_list=paper_list))


def export_command(*, tier: Tier, scope_id: str, dest: Path) -> Path:
    wing = _palace_root() / f"vedix_kg__{tier.value}__{scope_id}"
    if not wing.exists():
        raise FileNotFoundError(f"wing not found: {wing}")
    with tarfile.open(dest, "w:gz") as tf:
        tf.add(wing, arcname=wing.name)
    return dest


def import_command(*, tier: Tier, scope_id: str, src: Path) -> None:
    new_wing = _palace_root() / f"vedix_kg__{tier.value}__{scope_id}"
    if new_wing.exists():
        raise FileExistsError(f"target wing exists: {new_wing}")
    new_wing.parent.mkdir(parents=True, exist_ok=True)
    tmp = _palace_root().parent / "palace_import_tmp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    with tarfile.open(src, "r:gz") as tf:
        tf.extractall(tmp)
    extracted_dirs = [p for p in tmp.iterdir() if p.is_dir()]
    if len(extracted_dirs) != 1:
        raise RuntimeError("expected exactly one top-level directory in import tarball")
    shutil.move(str(extracted_dirs[0]), str(new_wing))
    shutil.rmtree(tmp, ignore_errors=True)


def gc_command(*, older_than_days: int = 30) -> list[str]:
    """Remove job-tier and reviewer-tier wings older than N days."""
    cutoff = time.time() - older_than_days * 86400
    removed: list[str] = []
    for wing in _palace_root().glob("vedix_kg__job__*"):
        if wing.stat().st_mtime < cutoff:
            shutil.rmtree(wing)
            removed.append(wing.name.removeprefix("vedix_kg__job__"))
    for wing in _palace_root().glob("vedix_kg__reviewer__*"):
        if wing.stat().st_mtime < cutoff:
            shutil.rmtree(wing)
            removed.append(wing.name.removeprefix("vedix_kg__reviewer__"))
    return removed


def add_paper_command(*, tier: Tier, scope_id: str, doi: str, pdf_path: Path) -> dict:
    """Manually add a paper (for the paywalled-paper case in spec §7.1)."""
    from .graph_builder import GraphBuilder
    import asyncio
    raw_dir = _job_raw_root(tier=tier, scope_id=scope_id)
    raw_dir.mkdir(parents=True, exist_ok=True)
    # Extract text from PDF using pdfminer
    from pdfminer.high_level import extract_text as _pdf_text
    text = _pdf_text(str(pdf_path))
    paper_id = doi.replace("/", "_")
    (raw_dir / f"{paper_id}.txt").write_text(text, encoding="utf-8")
    store = KGStore(tier=tier, scope_id=scope_id)
    builder = GraphBuilder(store=store, concurrency=1)
    return asyncio.run(builder.run(paper_list=[{"id": paper_id, "doi": doi,
                                                "title": "(user-provided)",
                                                "raw_text_path": str(raw_dir / f"{paper_id}.txt")}]))


def _job_raw_root(*, tier: Tier, scope_id: str) -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.environ["HOME"])
    if tier == Tier.JOB:
        return home / ".vedix" / "jobs" / scope_id / "raw"
    if tier == Tier.PROJECT:
        return home / ".vedix" / "projects" / scope_id / "raw_cache"
    return home / ".vedix" / "palace" / f"vedix_kg__{tier.value}__{scope_id}" / "raw"


def main():
    p = argparse.ArgumentParser(prog="vedix kg")
    sub = p.add_subparsers(dest="cmd", required=True)

    vp = sub.add_parser("verify")
    vp.add_argument("--tier", choices=[t.value for t in Tier], required=True)
    vp.add_argument("--scope-id", required=True)

    rp = sub.add_parser("rebuild")
    rp.add_argument("--tier", choices=[t.value for t in Tier], required=True)
    rp.add_argument("--scope-id", required=True)
    rp.add_argument("--paper-list", required=True, type=Path)

    ep = sub.add_parser("export")
    ep.add_argument("--tier", choices=[t.value for t in Tier], required=True)
    ep.add_argument("--scope-id", required=True)
    ep.add_argument("--dest", required=True, type=Path)

    ip = sub.add_parser("import")
    ip.add_argument("--tier", choices=[t.value for t in Tier], required=True)
    ip.add_argument("--scope-id", required=True)
    ip.add_argument("--src", required=True, type=Path)

    gp = sub.add_parser("gc")
    gp.add_argument("--older-than", type=int, default=30)

    ap = sub.add_parser("add-paper")
    ap.add_argument("--tier", choices=[t.value for t in Tier], required=True)
    ap.add_argument("--scope-id", required=True)
    ap.add_argument("--doi", required=True)
    ap.add_argument("--pdf", required=True, type=Path)

    args = p.parse_args()

    import json as _j
    if args.cmd == "verify":
        print(_j.dumps(verify_command(tier=Tier(args.tier), scope_id=args.scope_id), indent=2))
    elif args.cmd == "rebuild":
        print(_j.dumps(rebuild_command(tier=Tier(args.tier), scope_id=args.scope_id,
                                       paper_list_path=args.paper_list), indent=2))
    elif args.cmd == "export":
        out = export_command(tier=Tier(args.tier), scope_id=args.scope_id, dest=args.dest)
        print(f"exported to {out}")
    elif args.cmd == "import":
        import_command(tier=Tier(args.tier), scope_id=args.scope_id, src=args.src)
        print("imported")
    elif args.cmd == "gc":
        removed = gc_command(older_than_days=args.older_than)
        print(_j.dumps({"removed": removed}, indent=2))
    elif args.cmd == "add-paper":
        print(_j.dumps(add_paper_command(tier=Tier(args.tier), scope_id=args.scope_id,
                                         doi=args.doi, pdf_path=args.pdf), indent=2))


if __name__ == "__main__":
    main()
