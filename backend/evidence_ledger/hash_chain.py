"""Merkle-tree style hash chaining for tamper-evident evidence records."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))


def compute_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return compute_hash("")
    layer = hashes[:]
    while len(layer) > 1:
        if len(layer) % 2 == 1:
            layer.append(layer[-1])
        layer = [
            compute_hash(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)
        ]
    return layer[0]


@dataclass
class ChainEntry:
    record_id: str
    timestamp: datetime
    record_type: str
    payload: dict[str, Any]
    payload_hash: str
    previous_hash: str
    sequence_number: int
    entry_hash: str
    merkle_root: str


class HashChain:
    """Append-only hash chain with periodic Merkle root computation."""

    GENESIS_HASH = "0" * 64

    def __init__(self) -> None:
        self._entries: list[ChainEntry] = []
        self._pending_hashes: list[str] = []
        self._merkle_batch_size = 100

    @property
    def last_hash(self) -> str:
        if not self._entries:
            return self.GENESIS_HASH
        return self._entries[-1].entry_hash

    @property
    def sequence(self) -> int:
        return len(self._entries)

    def append(
        self,
        record_id: str,
        record_type: str,
        payload: dict[str, Any],
        timestamp: datetime | None = None,
    ) -> ChainEntry:
        ts = timestamp or datetime.now(timezone.utc)
        payload_hash = compute_hash(_canonical_json(payload))
        previous_hash = self.last_hash
        sequence_number = self.sequence

        entry_content = _canonical_json(
            {
                "record_id": record_id,
                "timestamp": ts.isoformat(),
                "record_type": record_type,
                "payload_hash": payload_hash,
                "previous_hash": previous_hash,
                "sequence_number": sequence_number,
            }
        )
        entry_hash = compute_hash(entry_content)

        self._pending_hashes.append(entry_hash)
        merkle_root = compute_merkle_root(self._pending_hashes)

        if len(self._pending_hashes) >= self._merkle_batch_size:
            self._pending_hashes = [merkle_root]

        entry = ChainEntry(
            record_id=record_id,
            timestamp=ts,
            record_type=record_type,
            payload=payload,
            payload_hash=payload_hash,
            previous_hash=previous_hash,
            sequence_number=sequence_number,
            entry_hash=entry_hash,
            merkle_root=merkle_root,
        )
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        expected_previous = self.GENESIS_HASH

        for entry in self._entries:
            if entry.previous_hash != expected_previous:
                errors.append(
                    f"Chain break at seq {entry.sequence_number}: "
                    f"expected prev {expected_previous[:16]}..., "
                    f"got {entry.previous_hash[:16]}..."
                )

            recomputed_payload_hash = compute_hash(_canonical_json(entry.payload))
            if recomputed_payload_hash != entry.payload_hash:
                errors.append(
                    f"Payload tamper detected at seq {entry.sequence_number}"
                )

            entry_content = _canonical_json(
                {
                    "record_id": entry.record_id,
                    "timestamp": entry.timestamp.isoformat(),
                    "record_type": entry.record_type,
                    "payload_hash": entry.payload_hash,
                    "previous_hash": entry.previous_hash,
                    "sequence_number": entry.sequence_number,
                }
            )
            if compute_hash(entry_content) != entry.entry_hash:
                errors.append(
                    f"Entry hash mismatch at seq {entry.sequence_number}"
                )

            expected_previous = entry.entry_hash

        return len(errors) == 0, errors

    def get_entries(
        self,
        record_type: str | None = None,
        limit: int = 100,
    ) -> list[ChainEntry]:
        entries = self._entries
        if record_type:
            entries = [e for e in entries if e.record_type == record_type]
        return entries[-limit:]

    def export_bundle(self, record_ids: list[str]) -> dict[str, Any]:
        selected = [e for e in self._entries if e.record_id in record_ids]
        valid, errors = self.verify_chain()
        return {
            "bundle_timestamp": datetime.now(timezone.utc).isoformat(),
            "chain_valid": valid,
            "verification_errors": errors,
            "merkle_root": selected[-1].merkle_root if selected else self.GENESIS_HASH,
            "records": [
                {
                    "record_id": e.record_id,
                    "timestamp": e.timestamp.isoformat(),
                    "record_type": e.record_type,
                    "payload": e.payload,
                    "payload_hash": e.payload_hash,
                    "entry_hash": e.entry_hash,
                    "previous_hash": e.previous_hash,
                    "sequence_number": e.sequence_number,
                }
                for e in selected
            ],
        }
