"""Permit log generator driven by scenario events."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.api.schemas import PermitRecord, PermitStatus, PermitType
from backend.config.settings import SCENARIO_PATH


class PermitLogGenerator:
    """Manages permit lifecycle based on scenario events."""

    def __init__(self, scenario_path: Path | None = None) -> None:
        path = scenario_path or SCENARIO_PATH
        with open(path, encoding="utf-8") as f:
            self.scenario = json.load(f)

        self.events = self.scenario["events"]
        self._permits: dict[str, PermitRecord] = {}
        self._current_tick = 0
        self._start_time = datetime.now(timezone.utc)

    def reset(self) -> None:
        self._permits = {}
        self._current_tick = 0
        self._start_time = datetime.now(timezone.utc)

    def tick(self) -> list[PermitRecord]:
        for event in self.events:
            if event["tick"] == self._current_tick:
                if event["type"] == "permit_approved":
                    self._create_permit(event["data"])

        self._current_tick += 1
        return list(self._permits.values())

    def _create_permit(self, data: dict[str, Any]) -> None:
        now = self._start_time + timedelta(seconds=self._current_tick)
        duration = timedelta(hours=data.get("duration_hours", 4))

        permit = PermitRecord(
            permit_id=data["permit_id"],
            permit_type=PermitType(data["permit_type"]),
            zone_id=data["zone_id"],
            status=PermitStatus.ACTIVE,
            requested_at=now - timedelta(minutes=14),
            approved_at=now,
            start_time=now,
            end_time=now + duration,
            requester=data["requester"],
            approver="Safety Officer - Priya Sharma",
            description=data["description"],
            latitude=data["latitude"],
            longitude=data["longitude"],
        )
        self._permits[permit.permit_id] = permit

    def get_active_permits(self) -> list[PermitRecord]:
        now = self._start_time + timedelta(seconds=self._current_tick)
        return [
            p
            for p in self._permits.values()
            if p.start_time <= now <= p.end_time
            and p.status in (PermitStatus.ACTIVE, PermitStatus.APPROVED)
        ]

    def add_permit(self, permit: PermitRecord) -> None:
        self._permits[permit.permit_id] = permit
