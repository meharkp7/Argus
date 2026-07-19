"""Pre-mortem permit simulation — evaluate risk before approval."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from backend.agents.permit_agent import PermitAgent
from backend.api.schemas import (
    CausalChainLink,
    PermitPreMortemRequest,
    PermitPreMortemResponse,
    PermitRecord,
    PermitStatus,
    SensorReading,
    ShiftRecord,
    WeatherReading,
)
from backend.permit_engine.rules import PermitRuleEngine
from backend.risk_graph.traversal import GraphTraverser, PlantState


class PreMortemSimulator:
    """Simulates compound risk if a proposed permit were approved now."""

    def __init__(self) -> None:
        self.rule_engine = PermitRuleEngine()
        self.permit_agent = PermitAgent()
        self.traverser = GraphTraverser()

    def simulate(
        self,
        request: PermitPreMortemRequest,
        current_permits: list[PermitRecord],
        sensor_readings: list[SensorReading],
        shifts: list[ShiftRecord] | None = None,
        weather: WeatherReading | None = None,
    ) -> PermitPreMortemResponse:
        proposed = PermitRecord(
            permit_id=f"PROPOSED-{uuid4().hex[:8]}",
            permit_type=request.permit_type,
            zone_id=request.zone_id,
            status=PermitStatus.PROPOSED,
            requested_at=datetime.now(timezone.utc),
            start_time=request.start_time,
            end_time=request.end_time,
            requester=request.requester,
            description=request.description,
            latitude=request.latitude,
            longitude=request.longitude,
        )

        anomaly_zones = list(
            {
                s.zone_id
                for s in sensor_readings
                if s.baseline_ppm > 0 and (s.value_ppm / s.baseline_ppm) >= 1.5
            }
        )

        violations = self.rule_engine.evaluate(
            proposed, current_permits, anomaly_zones
        )
        permit_analysis = self.permit_agent.evaluate_proposed_permit(
            proposed, current_permits, anomaly_zones
        )

        all_permits = current_permits + [proposed]
        state = PlantState(
            sensors=sensor_readings,
            permits=all_permits,
            shifts=shifts or [],
            weather=weather,
            timestamp=datetime.now(timezone.utc),
        )

        hazard_matches = self.traverser.match_hazards(state)
        top_match = hazard_matches[0] if hazard_matches else None

        risk_score = permit_analysis.risk_score
        if top_match:
            risk_score = max(risk_score, top_match.score)

        violation_msgs = [v.description for v in violations]
        warning_msgs = permit_analysis.warnings

        approved = len(violations) == 0 and risk_score < 0.7

        causal_factors: list[CausalChainLink] = []
        if top_match:
            causal_factors = top_match.causal_chain

        regulatory_citations = list({v.clause for v in violations})
        if top_match:
            regulatory_citations.extend(top_match.pattern.regulatory_references)

        reasoning = self._build_reasoning(
            proposed, violations, permit_analysis, top_match, approved
        )

        return PermitPreMortemResponse(
            approved_recommendation=approved,
            risk_score=round(risk_score, 3),
            confidence=round(top_match.score if top_match else permit_analysis.risk_score, 3),
            violations=violation_msgs,
            warnings=warning_msgs,
            reasoning=reasoning,
            causal_factors=causal_factors,
            regulatory_citations=list(set(regulatory_citations)),
        )

    def _build_reasoning(
        self,
        permit: PermitRecord,
        violations,
        analysis,
        top_match,
        approved: bool,
    ) -> str:
        parts = []

        if approved:
            parts.append(
                f"Pre-mortem simulation for {permit.permit_type.value} permit in "
                f"{permit.zone_id}: APPROVED with caution."
            )
        else:
            parts.append(
                f"Pre-mortem simulation for {permit.permit_type.value} permit in "
                f"{permit.zone_id}: NOT RECOMMENDED for approval."
            )

        if violations:
            parts.append(
                f"Regulatory violations detected: {'; '.join(v.description for v in violations)}."
            )

        if analysis.risk_flags:
            parts.append(f"Risk flags: {', '.join(analysis.risk_flags)}.")

        if top_match and top_match.score >= 0.5:
            parts.append(
                f"Compound hazard pattern '{top_match.pattern.name}' would be activated "
                f"(score: {top_match.score:.2f})."
            )

        if top_match and top_match.pattern.historical_precedents:
            parts.append(
                f"Historical precedent: {top_match.pattern.historical_precedents[0]}."
            )

        return " ".join(parts)
