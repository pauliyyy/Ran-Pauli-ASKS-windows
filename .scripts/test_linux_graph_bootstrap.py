#!/usr/bin/env python3
"""Pristine per-tenant document snapshots bootstrap only their owning graph."""
from pathlib import Path
import hashlib
import sqlite3
import tempfile
from unittest.mock import patch

import graph_lib as gl
import ingest_document as document


def test_pristine_graph_snapshot_preserves_public_private_boundaries():
    for domain, wiki in [("cross-domain", "academic/wiki/papers/demo.md"),
                         ("private", "private/wiki/notes/demo.md")]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            public = root / "cross-domain/graph.db"
            private = root / "private/graph.db"
            chosen = root / domain / "graph.db"
            other = private if domain == "cross-domain" else public
            state = {"wiki_path": wiki, "extract_dir": "temp/staging"}
            with patch.object(document, "REPO", root), patch.object(gl, "GRAPH_DB", public), patch.object(gl, "PRIVATE_GRAPH_DB", private):
                document.ensure_graph_snapshot(state)
                assert chosen.is_file() and not other.exists()
                snapshot = root / state["graph_snapshot"]
                assert snapshot.is_file() and Path(state["graph_db_path"]) == chosen
                for database in [chosen, snapshot]:
                    with sqlite3.connect(database) as conn:
                        assert conn.execute("SELECT count(*) FROM nodes").fetchone()[0] == 0
                        assert conn.execute("SELECT count(*) FROM edges").fetchone()[0] == 0
                before = hashlib.sha256(chosen.read_bytes()).hexdigest()
                document.ensure_graph_snapshot(state)
                assert hashlib.sha256(chosen.read_bytes()).hexdigest() == before


def test_existing_graph_snapshot_keeps_original_state():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        graph = root / "cross-domain/graph.db"
        graph.parent.mkdir(parents=True)
        with sqlite3.connect(graph) as conn:
            conn.execute("CREATE TABLE original(value TEXT)")
            conn.execute("INSERT INTO original VALUES ('preserved')")
        before = graph.read_bytes()
        state = {"wiki_path": "academic/wiki/papers/demo.md", "extract_dir": "temp/staging"}
        with patch.object(document, "REPO", root), patch.object(gl, "GRAPH_DB", graph):
            document.ensure_graph_snapshot(state)
        assert graph.read_bytes() == before
        with sqlite3.connect(root / state["graph_snapshot"]) as conn:
            assert conn.execute("SELECT value FROM original").fetchone() == ("preserved",)


if __name__ == "__main__":
    test_pristine_graph_snapshot_preserves_public_private_boundaries()
    test_existing_graph_snapshot_keeps_original_state()
    print("fresh per-tenant graph snapshot regression: PASS")
