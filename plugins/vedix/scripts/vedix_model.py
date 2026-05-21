"""``vedix model {fetch,publish,list}`` — distribute trained classifiers.

The model registry lives at ``$VEDIX_MODEL_REGISTRY`` (default
``https://models.vedix.ai/v1``). Each per-(discipline, language)
classifier is stored under its canonical name
``register_{discipline}_{language}/`` and consists of the four files
the trainer emits: ``model.safetensors``, ``config.json``,
``tokenizer.json``, ``metrics.json``.

Subcommands:
  • ``fetch`` — download canonical models into ``~/.vedix/classifiers``.
  • ``publish`` — POST a locally-trained model back to the registry.
    Refuses to publish without a ``metrics.json`` showing F1 ≥ 0.85.
  • ``list``  — print local classifiers with their F1 scores.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


REGISTRY_URL = os.environ.get("VEDIX_MODEL_REGISTRY", "https://models.vedix.ai/v1")
_MIN_F1 = 0.85


def _home() -> Path:
    return Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or ".")


def _classifiers_root() -> Path:
    return _home() / ".vedix" / "classifiers"


def fetch(
    *,
    languages: list[str],
    disciplines: list[str],
    registry_url: str | None = None,
    out_root: Path | None = None,
) -> dict:
    """Download every requested model into ``out_root``.

    Returns a per-pair status map ``{"register_<d>_<l>": {fn: status, ...}}``
    so callers can summarise failures.
    """
    import httpx

    base = (registry_url or REGISTRY_URL).rstrip("/")
    out = out_root or _classifiers_root()
    out.mkdir(parents=True, exist_ok=True)
    statuses: dict = {}
    with httpx.Client(timeout=120) as client:
        for d in disciplines:
            for l in languages:
                name = f"register_{d}_{l}"
                pair_dir = out / name
                pair_dir.mkdir(exist_ok=True)
                pair_status: dict = {}
                for fn in (
                    "model.safetensors",
                    "config.json",
                    "tokenizer.json",
                    "metrics.json",
                ):
                    url = f"{base}/{name}/{fn}"
                    try:
                        r = client.get(url)
                        if r.status_code == 200:
                            (pair_dir / fn).write_bytes(r.content)
                            pair_status[fn] = "ok"
                            print(f"  fetched {name}/{fn}")
                        else:
                            pair_status[fn] = f"http_{r.status_code}"
                            print(f"  miss {name}/{fn} (status {r.status_code})")
                    except Exception as e:
                        pair_status[fn] = f"error_{type(e).__name__}"
                        print(f"  error {name}/{fn}: {e}")
                statuses[name] = pair_status
    return statuses


def publish(
    *,
    name: str,
    model_dir: Path,
    registry_url: str | None = None,
) -> dict:
    """POST a locally-trained model up to the registry.

    Refuses to publish if ``metrics.json`` is missing or ``f1 < 0.85``.
    Returns a per-file status map.
    """
    import httpx

    base = (registry_url or REGISTRY_URL).rstrip("/")
    metrics_file = model_dir / "metrics.json"
    if not metrics_file.exists():
        raise SystemExit(
            f"{model_dir} missing metrics.json — cannot publish unvalidated model"
        )
    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    if metrics.get("f1", 0) < _MIN_F1:
        raise SystemExit(
            f"f1={metrics.get('f1')} < {_MIN_F1} — refusing to publish"
        )

    statuses: dict = {}
    with httpx.Client(timeout=300) as client:
        for fn in (
            "model.safetensors",
            "config.json",
            "tokenizer.json",
            "metrics.json",
        ):
            f = model_dir / fn
            if not f.exists():
                statuses[fn] = "missing"
                continue
            with f.open("rb") as fh:
                r = client.post(
                    f"{base}/{name}/{fn}",
                    files={"file": fh},
                )
            statuses[fn] = f"http_{r.status_code}"
            print(f"  POST {name}/{fn}: {r.status_code}")
    return statuses


def list_local(out_root: Path | None = None) -> list[dict]:
    """Return one entry per local classifier with its F1 score."""
    out = out_root or _classifiers_root()
    if not out.exists():
        return []
    rows = []
    for d in sorted(out.glob("register_*")):
        m_file = d / "metrics.json"
        m = json.loads(m_file.read_text(encoding="utf-8")) if m_file.exists() else {}
        row = {"name": d.name, "f1": m.get("f1"), "path": str(d)}
        rows.append(row)
        print(f"{d.name}\tf1={m.get('f1', '?')}")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(prog="vedix-model")
    sub = ap.add_subparsers(dest="cmd", required=True)

    fp = sub.add_parser("fetch")
    fp.add_argument("--languages", default="en,ru,es,de,fr,zh,ja")
    fp.add_argument(
        "--disciplines",
        default="chemistry,biology,medicine,physics,mathematics,geology,"
        "computer_science,humanities",
    )

    pp = sub.add_parser("publish")
    pp.add_argument("--name", required=True)
    pp.add_argument("--model-dir", required=True, type=Path)

    sub.add_parser("list")

    args = ap.parse_args()
    if args.cmd == "fetch":
        fetch(
            languages=[s.strip() for s in args.languages.split(",")],
            disciplines=[s.strip() for s in args.disciplines.split(",")],
        )
    elif args.cmd == "publish":
        publish(name=args.name, model_dir=args.model_dir)
    elif args.cmd == "list":
        list_local()


if __name__ == "__main__":  # pragma: no cover
    main()
