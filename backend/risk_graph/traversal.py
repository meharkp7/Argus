"""Real-time traversal of the causal risk graph against live plant state."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.api.schemas import (
    CausalChainLink,
    PermitRecord,
    SensorReading,
    ShiftRecord,
    WeatherReading,
)
from backend.risk_graph.causal_graph import CausalRiskGraph, HazardPattern, get_risk_graph


@dataclass
class PlantState:
    sensors: list[SensorReading] = field(default_factory=list)
    permits: list[PermitRecord] = field(default_factory=list)
    shifts: list[ShiftRecord] = field(default_factory=list)
    weather: WeatherReading | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    maintenance_status: dict[str, str] = field(default_factory=dict)


@dataclass
class ConditionEvaluation:
    node_id: str
    label: str
    satisfied: bool
    weight: float
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class HazardMatch:
    pattern: HazardPattern
    score: float
    satisfied_conditions: list[ConditionEvaluation]
    amplifying_conditions: list[ConditionEvaluation]
    causal_chain: list[CausalChainLink]
    zone_id: str


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class GraphTraverser:
    def __init__(self, graph: CausalRiskGraph | None = None) -> None:
        self.graph = graph or get_risk_graph()

    def evaluate_conditions(self, state: PlantState) -> dict[str, ConditionEvaluation]:
        results: dict[str, ConditionEvaluation] = {}

        for node_id, node in self.graph.condition_nodes.items():
            evaluation = self._evaluate_single_condition(node_id, node.evaluation, state)
            results[node_id] = evaluation

        return results

    def _evaluate_single_condition(
        self,
        node_id: str,
        evaluation: str,
        state: PlantState,
    ) -> ConditionEvaluation:
        node = self.graph.condition_nodes[node_id]

        if evaluation == "sensor_gas_ratio":
            return self._eval_gas_elevated(node, state)
        if evaluation == "h2s_drift_rate":
            return self._eval_h2s_drift(node, state)
        if evaluation == "permit_type_active":
            return self._eval_permit_active(node, state)
        if evaluation == "distance_meters":
            return self._eval_proximity(node, state)
        if evaluation == "wind_direction_to_zone":
            return self._eval_wind_toward_zone(node, state)
        if evaluation == "shift_changeover_window":
            return self._eval_shift_changeover(node, state)
        if evaluation == "contractor_ratio":
            return self._eval_contractor_crew(node, state)
        if evaluation == "night_shift_overtime":
            return self._eval_night_shift_fatigue(node, state)
        if evaluation == "simops_overlap":
            return self._eval_simops_overlap(node, state)
        if evaluation == "permit_complexity":
            return self._eval_complex_permit(node, state)
        if evaluation == "ventilation_status":
            return self._eval_ventilation(node, state)

        return ConditionEvaluation(
            node_id=node_id,
            label=node.label,
            satisfied=False,
            weight=0.0,
            evidence={"error": f"Unknown evaluation: {evaluation}"},
        )

    def _eval_gas_elevated(self, node, state: PlantState) -> ConditionEvaluation:
        threshold = node.threshold or 2.0
        max_ratio = 0.0
        best_sensor = None

        for sensor in state.sensors:
            if sensor.baseline_ppm <= 0:
                continue
            ratio = sensor.value_ppm / sensor.baseline_ppm
            if ratio > max_ratio:
                max_ratio = ratio
                best_sensor = sensor

        satisfied = max_ratio >= threshold
        weight = min(max_ratio / threshold, 2.0) if satisfied else max_ratio / threshold

        return ConditionEvaluation(
            node_id=node.id,
            label=node.label,
            satisfied=satisfied,
            weight=weight,
            evidence={
                "max_ratio": round(max_ratio, 2),
                "threshold": threshold,
                "sensor_id": best_sensor.sensor_id if best_sensor else None,
                "gas_type": best_sensor.gas_type if best_sensor else None,
                "value_ppm": best_sensor.value_ppm if best_sensor else None,
                "baseline_ppm": best_sensor.baseline_ppm if best_sensor else None,
            },
        )

    def _eval_h2s_drift(self, node, state: PlantState) -> ConditionEvaluation:
        threshold = node.threshold or 3.0
        h2s_sensors = [s for s in state.sensors if s.gas_type.upper() in ("H2S", "H₂S")]

        max_ratio = 0.0
        best_sensor = None
        for sensor in h2s_sensors:
            if sensor.baseline_ppm <= 0:
                continue
            ratio = sensor.value_ppm / sensor.baseline_ppm
            if ratio > max_ratio:
                max_ratio = ratio
                best_sensor = sensor

        satisfied = max_ratio >= threshold
        weight = min(max_ratio / threshold, 2.0) if satisfied else 0.0

        return ConditionEvaluation(
            node_id=node.id,
            label=node.label,
            satisfied=satisfied,
            weight=weight,
            evidence={
                "h2s_ratio": round(max_ratio, 2),
                "sensor_id": best_sensor.sensor_id if best_sensor else None,
            },
        )

    def _eval_permit_active(self, node, state: PlantState) -> ConditionEvaluation:
        permit_types = set(node.permit_types or [])
        active = [
            p
            for p in state.permits
            if p.status.value in ("active", "approved")
            and (not permit_types or p.permit_type.value in permit_types)
        ]
        satisfied = len(active) > 0

        return ConditionEvaluation(
            node_id=node.id,
            label=node.label,
            satisfied=satisfied,
            weight=1.0 if satisfied else 0.0,
            evidence={
                "active_permits": [p.permit_id for p in active],
                "permit_types": list({p.permit_type.value for p in active}),
                "zones": list({p.zone_id for p in active}),
            },
        )

    def _eval_proximity(self, node, state: PlantState) -> ConditionEvaluation:
        threshold = node.threshold or 50.0
        min_distance = float("inf")
        closest_pair = None

        anomalous_sensors = [
            s
            for s in state.sensors
            if s.baseline_ppm > 0 and (s.value_ppm / s.baseline_ppm) >= 1.5
        ]
        active_permits = [
            p for p in state.permits if p.status.value in ("active", "approved")
        ]

        for sensor in anomalous_sensors:
            if sensor.latitude is None or sensor.longitude is None:
                continue
            for permit in active_permits:
                dist = _haversine_distance(
                    sensor.latitude,
                    sensor.longitude,
                    permit.latitude,
                    permit.longitude,
                )
                if dist < min_distance:
                    min_distance = dist
                    closest_pair = (sensor.sensor_id, permit.permit_id)

        satisfied = min_distance <= threshold
        weight = max(0, 1.0 - (min_distance / threshold)) if min_distance < float("inf") else 0.0

        return ConditionEvaluation(
            node_id=node.id,
            label=node.label,
            satisfied=satisfied,
            weight=weight if satisfied else 0.0,
            evidence={
                "min_distance_m": round(min_distance, 1) if min_distance < float("inf") else None,
                "threshold_m": threshold,
                "closest_pair": closest_pair,
            },
        )

    def _eval_wind_toward_zone(self, node, state: PlantState) -> ConditionEvaluation:
        if not state.weather:
            return ConditionEvaluation(node.id, node.label, False, 0.0)

        anomalous = [
            s
            for s in state.sensors
            if s.baseline_ppm > 0 and (s.value_ppm / s.baseline_ppm) >= 1.5
        ]
        active_permits = [
            p for p in state.permits if p.status.value in ("active", "approved")
        ]

        if not anomalous or not active_permits:
            return ConditionEvaluation(node.id, node.label, False, 0.0)

        wind_rad = math.radians(state.weather.wind_direction_deg)
        wind_vector = (math.sin(wind_rad), math.cos(wind_rad))

        for sensor in anomalous:
            if sensor.latitude is None:
                continue
            for permit in active_permits:
                if permit.latitude is None:
                    continue
                dx = permit.longitude - sensor.longitude
                dy = permit.latitude - sensor.latitude
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 1e-9:
                    continue
                direction = (dx / dist, dy / dist)
                alignment = wind_vector[0] * direction[0] + wind_vector[1] * direction[1]
                if alignment > 0.3:
                    return ConditionEvaluation(
                        node.id,
                        node.label,
                        True,
                        min(alignment, 1.0),
                        evidence={
                            "wind_direction_deg": state.weather.wind_direction_deg,
                            "wind_speed_ms": state.weather.wind_speed_ms,
                            "sensor_id": sensor.sensor_id,
                            "permit_id": permit.permit_id,
                            "alignment": round(alignment, 2),
                        },
                    )

        return ConditionEvaluation(node.id, node.label, False, 0.0)

    def _eval_shift_changeover(self, node, state: PlantState) -> ConditionEvaluation:
        window = timedelta(minutes=node.window_minutes or 30)
        now = state.timestamp

        for shift in state.shifts:
            for boundary in (shift.start_time, shift.end_time):
                if abs(now - boundary) <= window:
                    return ConditionEvaluation(
                        node.id,
                        node.label,
                        True,
                        1.0,
                        evidence={
                            "shift_id": shift.shift_id,
                            "boundary": boundary.isoformat(),
                            "minutes_to_boundary": abs((now - boundary).total_seconds()) / 60,
                        },
                    )

        return ConditionEvaluation(node.id, node.label, False, 0.0)

    def _eval_contractor_crew(self, node, state: PlantState) -> ConditionEvaluation:
        threshold = node.threshold or 0.5
        max_ratio = max((s.contractor_ratio for s in state.shifts), default=0.0)
        satisfied = max_ratio >= threshold

        return ConditionEvaluation(
            node.id,
            node.label,
            satisfied,
            max_ratio if satisfied else 0.0,
            evidence={"contractor_ratio": max_ratio, "threshold": threshold},
        )

    def _eval_night_shift_fatigue(self, node, state: PlantState) -> ConditionEvaluation:
        for shift in state.shifts:
            if shift.is_night_shift and shift.overtime_hours > 0:
                weight = min(1.0, 0.5 + shift.overtime_hours * 0.1)
                return ConditionEvaluation(
                    node.id,
                    node.label,
                    True,
                    weight,
                    evidence={
                        "shift_id": shift.shift_id,
                        "overtime_hours": shift.overtime_hours,
                        "is_night_shift": True,
                    },
                )
        return ConditionEvaluation(node.id, node.label, False, 0.0)

    def _eval_simops_overlap(self, node, state: PlantState) -> ConditionEvaluation:
        high_risk_types = {"hot_work", "confined_space", "lifting"}
        active = [
            p
            for p in state.permits
            if p.status.value in ("active", "approved")
            and p.permit_type.value in high_risk_types
        ]

        zones_with_multiple: dict[str, list[str]] = {}
        for permit in active:
            zones_with_multiple.setdefault(permit.zone_id, []).append(permit.permit_id)

        overlapping = {z: pids for z, pids in zones_with_multiple.items() if len(pids) > 1}
        satisfied = len(overlapping) > 0

        return ConditionEvaluation(
            node.id,
            node.label,
            satisfied,
            1.0 if satisfied else 0.0,
            evidence={"overlapping_zones": overlapping},
        )

    def _eval_complex_permit(self, node, state: PlantState) -> ConditionEvaluation:
        complex_types = set(node.permit_types or ["hot_work", "confined_space", "lifting"])
        active = [
            p
            for p in state.permits
            if p.status.value in ("active", "approved")
            and p.permit_type.value in complex_types
        ]
        satisfied = len(active) > 0

        return ConditionEvaluation(
            node.id,
            node.label,
            satisfied,
            1.0 if satisfied else 0.0,
            evidence={"complex_permits": [p.permit_id for p in active]},
        )

    def _eval_ventilation(self, node, state: PlantState) -> ConditionEvaluation:
        inadequate_zones = [
            zone
            for zone, status in state.maintenance_status.items()
            if status.lower() in ("offline", "maintenance", "failed")
        ]
        satisfied = len(inadequate_zones) > 0

        return ConditionEvaluation(
            node.id,
            node.label,
            satisfied,
            1.0 if satisfied else 0.0,
            evidence={"inadequate_ventilation_zones": inadequate_zones},
        )

    def match_hazards(self, state: PlantState) -> list[HazardMatch]:
        conditions = self.evaluate_conditions(state)
        matches: list[HazardMatch] = []

        for pattern in self.graph.hazard_patterns:
            required_met = True
            required_score = 0.0
            satisfied_required: list[ConditionEvaluation] = []

            for req in pattern.required_conditions:
                node_id = req["node"]
                min_weight = req.get("min_weight", 0.5)
                cond = conditions.get(node_id)

                if not cond or not cond.satisfied or cond.weight < min_weight:
                    required_met = False
                    break

                required_score += cond.weight
                satisfied_required.append(cond)

            if not required_met:
                continue

            amplifying: list[ConditionEvaluation] = []
            amplifying_score = 0.0
            for amp in pattern.amplifying_conditions:
                node_id = amp["node"]
                amp_weight = amp.get("weight", 0.1)
                cond = conditions.get(node_id)
                if cond and cond.satisfied:
                    amplifying.append(cond)
                    amplifying_score += amp_weight * cond.weight

            base_score = required_score / max(len(pattern.required_conditions), 1)
            total_score = min(1.0, base_score * 0.7 + amplifying_score * 0.3 + 0.1)

            causal_chain = self._build_causal_chain(
                pattern, satisfied_required, amplifying
            )

            zone_id = self._determine_primary_zone(state, satisfied_required)

            matches.append(
                HazardMatch(
                    pattern=pattern,
                    score=total_score,
                    satisfied_conditions=satisfied_required,
                    amplifying_conditions=amplifying,
                    causal_chain=causal_chain,
                    zone_id=zone_id,
                )
            )

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    def _build_causal_chain(
        self,
        pattern: HazardPattern,
        required: list[ConditionEvaluation],
        amplifying: list[ConditionEvaluation],
    ) -> list[CausalChainLink]:
        chain: list[CausalChainLink] = []

        for cond in required:
            chain.append(
                CausalChainLink(
                    node_id=cond.node_id,
                    label=cond.label,
                    description=f"Required condition met: {cond.label}",
                    evidence=cond.evidence,
                    weight=cond.weight,
                )
            )

        for cond in amplifying:
            chain.append(
                CausalChainLink(
                    node_id=cond.node_id,
                    label=cond.label,
                    description=f"Amplifying factor: {cond.label}",
                    evidence=cond.evidence,
                    weight=cond.weight * 0.5,
                )
            )

        chain.append(
            CausalChainLink(
                node_id=pattern.id,
                label=pattern.name,
                description=pattern.description,
                evidence={
                    "historical_precedents": pattern.historical_precedents,
                    "regulatory_references": pattern.regulatory_references,
                },
                weight=1.0,
            )
        )

        return chain

    def _determine_primary_zone(
        self,
        state: PlantState,
        conditions: list[ConditionEvaluation],
    ) -> str:
        zone_counts: dict[str, int] = {}

        for permit in state.permits:
            if permit.status.value in ("active", "approved"):
                zone_counts[permit.zone_id] = zone_counts.get(permit.zone_id, 0) + 2

        for sensor in state.sensors:
            if sensor.baseline_ppm > 0 and (sensor.value_ppm / sensor.baseline_ppm) >= 1.5:
                zone_counts[sensor.zone_id] = zone_counts.get(sensor.zone_id, 0) + 1

        if zone_counts:
            return max(zone_counts, key=zone_counts.get)

        if state.permits:
            return state.permits[0].zone_id
        if state.sensors:
            return state.sensors[0].zone_id
        return "ZONE-C"
