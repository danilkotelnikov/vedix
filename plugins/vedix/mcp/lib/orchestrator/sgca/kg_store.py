from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional
from .schema import KGFragment, Edge, ConceptLatticeEntry, NodeId


class Tier(str, Enum):
    JOB = "job"
    REVIEWER = "reviewer"
    PROJECT = "project"
    NICHE = "niche"


def _palace_root() -> Path:
    home = Path(os.environ.get("USERPROFILE") or os.environ["HOME"])
    root = home / ".vedix" / "palace"
    root.mkdir(parents=True, exist_ok=True)
    return root


class KGStore:
    """MemPalace-backed KG store. Each (tier, scope_id) maps to one wing
    (`vedix_kg__<tier>__<scope_id>/`) backed by a SQLite database."""

    def __init__(self, tier: Tier, scope_id: str):
        self.tier = tier
        self.scope_id = scope_id
        self.wing = _palace_root() / f"vedix_kg__{tier.value}__{scope_id}"
        self.wing.mkdir(parents=True, exist_ok=True)
        (self.wing / "drawers").mkdir(exist_ok=True)
        (self.wing / "tunnels").mkdir(exist_ok=True)
        self.db_path = self.wing / "tunnels" / "edges.sqlite"
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    confidence REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_edges_from ON edges (from_node);
                CREATE INDEX IF NOT EXISTS idx_edges_to ON edges (to_node);
                CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges (kind);
                CREATE TABLE IF NOT EXISTS lattice (
                    concept_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def write_paper(self, frag: KGFragment) -> None:
        out = self.wing / "drawers" / f"paper__{frag.paper_id}.json"
        out.write_text(frag.model_dump_json(indent=2, by_alias=True), encoding="utf-8")
        for edge in frag.edges:
            self.write_edge(edge)
        self._bump_revision()

    def read_paper(self, paper_id: str) -> Optional[KGFragment]:
        f = self.wing / "drawers" / f"paper__{paper_id}.json"
        if not f.exists():
            return None
        return KGFragment.model_validate_json(f.read_text(encoding="utf-8"))

    def list_paper_ids(self) -> list[str]:
        return [p.stem.removeprefix("paper__")
                for p in (self.wing / "drawers").glob("paper__*.json")]

    def write_edge(self, edge: Edge) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT INTO edges (from_node, to_node, kind, confidence) VALUES (?, ?, ?, ?)",
                (edge.from_, edge.to, edge.kind, edge.confidence),
            )
        self._bump_revision()

    def edges_from(self, node_id: NodeId) -> list[Edge]:
        with self._conn() as c:
            rows = c.execute("SELECT from_node, to_node, kind, confidence FROM edges WHERE from_node = ?",
                             (node_id,)).fetchall()
        return [Edge(**{"from": r["from_node"], "to": r["to_node"], "kind": r["kind"], "confidence": r["confidence"]})
                for r in rows]

    def edges_to(self, node_id: NodeId) -> list[Edge]:
        with self._conn() as c:
            rows = c.execute("SELECT from_node, to_node, kind, confidence FROM edges WHERE to_node = ?",
                             (node_id,)).fetchall()
        return [Edge(**{"from": r["from_node"], "to": r["to_node"], "kind": r["kind"], "confidence": r["confidence"]})
                for r in rows]

    def write_lattice_entry(self, entry: ConceptLatticeEntry) -> None:
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO lattice (concept_id, payload) VALUES (?, ?)",
                      (entry.id, entry.model_dump_json()))
        self._bump_revision()

    def read_lattice_entry(self, concept_id: str) -> Optional[ConceptLatticeEntry]:
        with self._conn() as c:
            row = c.execute("SELECT payload FROM lattice WHERE concept_id = ?", (concept_id,)).fetchone()
        if not row:
            return None
        return ConceptLatticeEntry.model_validate_json(row["payload"])

    def all_lattice_entries(self) -> list[ConceptLatticeEntry]:
        with self._conn() as c:
            rows = c.execute("SELECT payload FROM lattice").fetchall()
        return [ConceptLatticeEntry.model_validate_json(r["payload"]) for r in rows]

    def _bump_revision(self) -> None:
        cur = self.kg_revision_id()
        nxt = hashlib.sha256(f"{cur}|{os.urandom(8).hex()}".encode()).hexdigest()[:16]
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('kg_revision_id', ?)", (nxt,))

    def kg_revision_id(self) -> str:
        with self._conn() as c:
            row = c.execute("SELECT value FROM meta WHERE key = 'kg_revision_id'").fetchone()
        return row["value"] if row else "init"
