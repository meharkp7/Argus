"""Explainer agent — converts graph traversal into plain-language causal narratives."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from backend.api.schemas import CompoundAlert
from backend.config.settings import get_settings
from backend.risk_graph.causal_graph import get_risk_graph


class ExplainerAgent:
    """Generates human-readable explanations for compound risk alerts."""

    SYSTEM_PROMPT = """You are ARGUS, an industrial safety intelligence system for Indian heavy industry.
Your role is to explain compound risk alerts in plain language that a safety officer, regulator, and frontline worker can all understand.

Rules:
- Always explain the CAUSAL CHAIN — which conditions combined and WHY they are dangerous together
- Reference specific sensor IDs, permit IDs, and measurements from the evidence
- Mention historical precedents when available
- Cite relevant regulatory frameworks (OISD, DGMS, Factory Act) when applicable
- Be direct and actionable — no hedging
- Keep explanations to 3-5 sentences maximum
- Never hallucinate data not present in the evidence"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.graph = get_risk_graph()
        self._client: anthropic.Anthropic | None = None
        if self.settings.anthropic_api_key:
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    def explain(self, alert: CompoundAlert) -> str:
        if self._client:
            try:
                return self._llm_explain(alert)
            except Exception:
                pass

        return self._template_explain(alert)

    def _llm_explain(self, alert: CompoundAlert) -> str:
        evidence = {
            "alert_id": alert.alert_id,
            "severity": alert.severity.value,
            "confidence": alert.confidence,
            "zone_id": alert.zone_id,
            "hazard_pattern_id": alert.hazard_pattern_id,
            "causal_chain": [link.model_dump() for link in alert.causal_chain],
            "sensor_ids": alert.sensor_ids,
            "permit_ids": alert.permit_ids,
            "recommended_actions": alert.recommended_actions,
            "lead_time_minutes": alert.lead_time_minutes,
        }

        response = self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=500,
            system=self.SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Explain this compound risk alert:\n{json.dumps(evidence, indent=2, default=str)}",
                }
            ],
        )

        return response.content[0].text

    def _template_explain(self, alert: CompoundAlert) -> str:
        pattern = self.graph.get_hazard_pattern(alert.hazard_pattern_id)
        pattern_name = pattern.name if pattern else alert.hazard_pattern_id

        parts: list[str] = []
        parts.append(
            f"COMPOUND RISK ALERT — {pattern_name} detected in {alert.zone_id} "
            f"(confidence: {alert.confidence:.0%}, severity: {alert.severity.value})."
        )

        condition_descriptions = []
        for link in alert.causal_chain:
            if link.node_id.startswith("HP-"):
                continue
            evidence_summary = self._summarize_evidence(link.evidence)
            if evidence_summary:
                condition_descriptions.append(f"{link.label}: {evidence_summary}")
            else:
                condition_descriptions.append(link.label)

        if condition_descriptions:
            parts.append(
                "Causal chain: " + "; ".join(condition_descriptions) + "."
            )

        if alert.permit_ids:
            parts.append(
                f"Active permits involved: {', '.join(alert.permit_ids)}."
            )

        if alert.sensor_ids:
            parts.append(
                f"Anomalous sensors: {', '.join(alert.sensor_ids)}."
            )

        if pattern and pattern.historical_precedents:
            parts.append(
                f"Historical precedent: this pattern preceded incidents including "
                f"{pattern.historical_precedents[0]}."
            )

        if alert.lead_time_minutes:
            parts.append(
                f"Estimated lead time before threshold breach: {alert.lead_time_minutes:.0f} minutes."
            )

        if not alert.baseline_would_trigger:
            parts.append(
                "Note: single-sensor threshold baseline would NOT have triggered this alert."
            )

        return " ".join(parts)

    def _summarize_evidence(self, evidence: dict[str, Any]) -> str:
        parts = []
        if "sensor_id" in evidence and evidence["sensor_id"]:
            ratio = evidence.get("max_ratio") or evidence.get("h2s_ratio")
            if ratio:
                parts.append(
                    f"sensor {evidence['sensor_id']} at {ratio}x baseline"
                )
            else:
                parts.append(f"sensor {evidence['sensor_id']}")

        if "active_permits" in evidence and evidence["active_permits"]:
            parts.append(f"permits {', '.join(evidence['active_permits'])}")

        if "min_distance_m" in evidence and evidence["min_distance_m"] is not None:
            parts.append(f"{evidence['min_distance_m']}m proximity")

        if "wind_direction_deg" in evidence:
            parts.append(
                f"wind {evidence['wind_direction_deg']}° at {evidence.get('wind_speed_ms', '?')} m/s"
            )

        if "contractor_ratio" in evidence:
            parts.append(f"contractor ratio {evidence['contractor_ratio']:.0%}")

        if "overtime_hours" in evidence:
            parts.append(f"{evidence['overtime_hours']}h overtime on night shift")

        return ", ".join(parts)
