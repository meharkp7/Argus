"""Correlation agent — traverses causal risk graph linking sensor and permit outputs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.agents.permit_agent import PermitAnalysis
from backend.agents.sensor_agent import SensorAnomaly
from backend.api.schemas import (
    AlertSeverity,
    CausalChainLink,
    CompoundAlert,
    ConfidenceBand,
    PermitRecord,
    SensorReading,
    ShiftRecord,
    WeatherReading,
)
from backend.risk_graph.traversal import GraphTraverser, HazardMatch, PlantState
from backend.trust_calibration.threshold_updater import get_threshold_updater


@dataclass
class CorrelationResult:
    alerts: list[CompoundAlert] = field(default_factory=list)
    hazard_matches: list[HazardMatch] = field(default_factory=list)
    baseline_would_trigger: bool = False
    plant_state: PlantState | None = None


class CorrelationAgent:
    """Fuses agent outputs via causal risk graph traversal."""

    SEVERITY_MAP = {
        "critical": AlertSeverity.CRITICAL,
        "high": AlertSeverity.HIGH,
        "medium": AlertSeverity.MEDIUM,
        "low": AlertSeverity.LOW,
    }

    def __init__(self) -> None:
        self.traverser = GraphTraverser()
        self.threshold_updater = get_threshold_updater()

    def correlate(
        self,
        sensor_readings: list[SensorReading],
        sensor_anomalies: list[SensorAnomaly],
        permit_analyses: list[PermitAnalysis],
        permits: list[PermitRecord],
        shifts: list[ShiftRecord],
        weather: WeatherReading | None,
        baseline_would_trigger: bool = False,
        maintenance_status: dict[str, str] | None = None,
    ) -> CorrelationResult:
        state = PlantState(
            sensors=sensor_readings,
            permits=permits,
            shifts=shifts,
            weather=weather,
            timestamp=datetime.now(timezone.utc),
            maintenance_status=maintenance_status or {},
        )

        hazard_matches = self.traverser.match_hazards(state)
        thresholds = self.threshold_updater.get_current_thresholds()
        compound_threshold = thresholds["compound_risk_threshold"]

        alerts: list[CompoundAlert] = []
        for match in hazard_matches:
            if match.score < compound_threshold:
                continue

            confidence = self._compute_confidence(match, sensor_anomalies, permit_analyses)
            confidence_band = self._confidence_band(confidence)

            alert = CompoundAlert(
                alert_id=str(uuid4()),
                timestamp=state.timestamp,
                severity=self.SEVERITY_MAP.get(
                    match.pattern.severity, AlertSeverity.HIGH
                ),
                confidence=round(confidence, 3),
                confidence_band=confidence_band,
                zone_id=match.zone_id,
                hazard_pattern_id=match.pattern.id,
                causal_chain=match.causal_chain,
                explanation="",
                recommended_actions=match.pattern.recommended_actions,
                lead_time_minutes=self._estimate_lead_time(match, sensor_anomalies),
                sensor_ids=self._extract_sensor_ids(match),
                permit_ids=self._extract_permit_ids(match),
                baseline_would_trigger=baseline_would_trigger,
            )
            alerts.append(alert)

        return CorrelationResult(
            alerts=alerts,
            hazard_matches=hazard_matches,
            baseline_would_trigger=baseline_would_trigger,
            plant_state=state,
        )

    def _compute_confidence(
        self,
        match: HazardMatch,
        anomalies: list[SensorAnomaly],
        permit_analyses: list[PermitAnalysis],
    ) -> float:
        base = match.score

        critical_anomalies = sum(1 for a in anomalies if a.severity == "critical")
        if critical_anomalies > 0:
            base += 0.1

        high_risk_permits = sum(1 for p in permit_analyses if p.risk_score > 0.5)
        if high_risk_permits > 0:
            base += 0.05 * min(high_risk_permits, 3)

        amplifying_count = len(match.amplifying_conditions)
        base += 0.03 * amplifying_count

        return min(base, 0.99)

    def _confidence_band(self, confidence: float) -> ConfidenceBand:
        settings_threshold_high = 0.85
        settings_threshold_medium = 0.65
        if confidence >= settings_threshold_high:
            return ConfidenceBand.HIGH
        if confidence >= settings_threshold_medium:
            return ConfidenceBand.MEDIUM
        return ConfidenceBand.LOW

    def _estimate_lead_time(
        self,
        match: HazardMatch,
        anomalies: list[SensorAnomaly],
    ) -> float | None:
        if not anomalies:
            return None

        max_ratio = max(a.ratio_to_baseline for a in anomalies)
        if max_ratio < 2.0:
            return 15.0
        if max_ratio < 3.0:
            return 8.0
        return 3.0

    def _extract_sensor_ids(self, match: HazardMatch) -> list[str]:
        ids: list[str] = []
        for cond in match.satisfied_conditions + match.amplifying_conditions:
            sensor_id = cond.evidence.get("sensor_id")
            if sensor_id and sensor_id not in ids:
                ids.append(sensor_id)
        return ids

    def _extract_permit_ids(self, match: HazardMatch) -> list[str]:
        ids: list[str] = []
        for cond in match.satisfied_conditions + match.amplifying_conditions:
            permit_list = cond.evidence.get("active_permits", [])
            for pid in permit_list:
                if pid not in ids:
                    ids.append(pid)
            if "permit_id" in cond.evidence:
                pid = cond.evidence["permit_id"]
                if pid not in ids:
                    ids.append(pid)
        return ids
