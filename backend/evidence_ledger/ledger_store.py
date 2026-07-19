"""Persistent evidence ledger storage backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.config.settings import LEDGER_DB_PATH
from backend.evidence_ledger.hash_chain import ChainEntry, HashChain


class LedgerStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or LEDGER_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._chain = HashChain()
        self._init_db()
        self._load_chain()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evidence_records (
                    record_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL,
                    merkle_root TEXT NOT NULL,
                    sequence_number INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_evidence_type
                ON evidence_records(record_type)
                """
            )
            conn.commit()

    def _load_chain(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM evidence_records
                ORDER BY sequence_number ASC
                """
            ).fetchall()

        for row in rows:
            payload = json.loads(row["payload"])
            entry = ChainEntry(
                record_id=row["record_id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                record_type=row["record_type"],
                payload=payload,
                payload_hash=row["payload_hash"],
                previous_hash=row["previous_hash"],
                sequence_number=row["sequence_number"],
                entry_hash=row["entry_hash"],
                merkle_root=row["merkle_root"],
            )
            self._chain._entries.append(entry)
            self._chain._pending_hashes.append(entry.entry_hash)

    def record(
        self,
        record_type: str,
        payload: dict[str, Any],
        record_id: str | None = None,
        timestamp: datetime | None = None,
    ) -> ChainEntry:
        rid = record_id or str(uuid4())
        entry = self._chain.append(rid, record_type, payload, timestamp)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO evidence_records
                (record_id, timestamp, record_type, payload, payload_hash,
                 previous_hash, entry_hash, merkle_root, sequence_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.record_id,
                    entry.timestamp.isoformat(),
                    entry.record_type,
                    json.dumps(entry.payload, default=str),
                    entry.payload_hash,
                    entry.previous_hash,
                    entry.entry_hash,
                    entry.merkle_root,
                    entry.sequence_number,
                ),
            )
            conn.commit()
        return entry

    def verify(self) -> tuple[bool, list[str]]:
        return self._chain.verify_chain()

    def get_records(
        self,
        record_type: str | None = None,
        limit: int = 100,
    ) -> list[ChainEntry]:
        return self._chain.get_entries(record_type, limit)

    def export_evidence_bundle(self, record_ids: list[str]) -> dict[str, Any]:
        return self._chain.export_bundle(record_ids)

    @property
    def merkle_root(self) -> str:
        entries = self._chain.get_entries()
        if not entries:
            return HashChain.GENESIS_HASH
        return entries[-1].merkle_root


_ledger_instance: LedgerStore | None = None


def get_ledger() -> LedgerStore:
    global _ledger_instance
    if _ledger_instance is None:
        _ledger_instance = LedgerStore()
    return _ledger_instance
