"""Permit activity analysis with rule-based and contextual reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.api.schemas import PermitRecord, PermitStatus, PermitType
from backend.risk_graph.causal_graph import get_risk_graph


@dataclass
class PermitAnalysis:
    permit_id: str
    zone_id: str
    permit_type: str
    risk_flags: list[str]
    risk_score: float
    violations: list[str]
    warnings: list[str]
    details: dict[str, Any] = field(default_factory=dict)


class PermitAgent:
    """Analyzes active and proposed permits against plant safety rules."""

    SIMOPS_CONFLICTS = {
        PermitType.HOT_WORK: {PermitType.CONFINED_SPACE, PermitType.LIFTING},
        PermitType.CONFINED_SPACE: {PermitType.HOT_WORK, PermitType.EXCAVATION},
        PermitType.LIFTING: {PermitType.HOT_WORK},
    }

    HIGH_RISK_ZONES = {"ZONE-C", "ZONE-D"}

    def __init__(self) -> None:
        self.graph = get_risk_graph()

    def analyze_permits(
        self,
        permits: list[PermitRecord],
        current_time: datetime | None = None,
    ) -> list[PermitAnalysis]:
        now = current_time or datetime.now(timezone.utc)
        active = [
            p
            for p in permits
            if p.status in (PermitStatus.ACTIVE, PermitStatus.APPROVED)
            and p.start_time <= now <= p.end_time
        ]

        analyses = []
        for permit in active:
            analysis = self._analyze_single(permit, active, now)
            analyses.append(analysis)

        return analyses

    def _analyze_single(
        self,
        permit: PermitRecord,
        all_active: list[PermitRecord],
        now: datetime,
    ) -> PermitAnalysis:
        flags: list[str] = []
        violations: list[str] = []
        warnings: list[str] = []
        risk_score = 0.0

        if permit.permit_type == PermitType.HOT_WORK:
            risk_score += 0.3
            flags.append("hot_work_active")

        if permit.zone_id in self.HIGH_RISK_ZONES:
            risk_score += 0.2
            warnings.append(f"Permit in high-risk zone {permit.zone_id}")

        for other in all_active:
            if other.permit_id == permit.permit_id:
                continue
            if other.zone_id == permit.zone_id:
                conflicts = self.SIMOPS_CONFLICTS.get(permit.permit_type, set())
                if other.permit_type in conflicts:
                    violations.append(
                        f"SIMOPS conflict: {permit.permit_type.value} with "
                        f"{other.permit_type.value} (permit {other.permit_id})"
                    )
                    risk_score += 0.4
                    flags.append("simops_conflict")

        duration_hours = (permit.end_time - permit.start_time).total_seconds() / 3600
        if duration_hours > 8:
            warnings.append(f"Extended permit duration: {duration_hours:.1f} hours")
            risk_score += 0.1

        if permit.permit_type == PermitType.HOT_WORK and permit.zone_id == "ZONE-C":
            risk_score += 0.25
            flags.append("hot_work_in_gas_monitoring_zone")

        return PermitAnalysis(
            permit_id=permit.permit_id,
            zone_id=permit.zone_id,
            permit_type=permit.permit_type.value,
            risk_flags=flags,
            risk_score=min(risk_score, 1.0),
            violations=violations,
            warnings=warnings,
            details={
                "status": permit.status.value,
                "requester": permit.requester,
                "description": permit.description,
            },
        )

    def evaluate_proposed_permit(
        self,
        permit: PermitRecord,
        existing_permits: list[PermitRecord],
        sensor_anomaly_zones: list[str] | None = None,
    ) -> PermitAnalysis:
        analysis = self._analyze_single(
            permit, existing_permits + [permit], datetime.now(timezone.utc)
        )

        if sensor_anomaly_zones and permit.zone_id in sensor_anomaly_zones:
            analysis.violations.append(
                f"Proposed permit in zone {permit.zone_id} with active sensor anomalies"
            )
            analysis.risk_score = min(1.0, analysis.risk_score + 0.5)
            analysis.risk_flags.append("sensor_anomaly_in_zone")

        adjacent = self.graph.get_adjacent_zones(permit.zone_id)
        if sensor_anomaly_zones:
            for adj_zone in adjacent:
                if adj_zone in sensor_anomaly_zones:
                    analysis.warnings.append(
                        f"Adjacent zone {adj_zone} has sensor anomalies"
                    )
                    analysis.risk_score = min(1.0, analysis.risk_score + 0.2)

        return analysis
