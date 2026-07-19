"""Auto-drafted regulatory-format incident report generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import anthropic

from backend.api.schemas import CompoundAlert, IncidentReportDraft, PermitRecord, SensorReading
from backend.config.settings import get_settings
from backend.evidence_ledger.ledger_store import get_ledger


class IncidentReportGenerator:
    """Generates preliminary regulatory-format incident reports from evidence."""

    REPORT_TEMPLATE = {
        "incident_summary": "",
        "immediate_actions_taken": "",
        "affected_zones_and_equipment": "",
        "sensor_data_summary": "",
        "permit_status_at_time": "",
        "causal_analysis": "",
        "regulatory_notifications_required": "",
        "evidence_chain_reference": "",
        "recommended_follow_up": "",
    }

    def __init__(self) -> None:
        self.settings = get_settings()
        self.ledger = get_ledger()
        self._client: anthropic.Anthropic | None = None
        if self.settings.anthropic_api_key:
            self._client = anthropic.Anthropic(api_key=self.settings.anthropic_api_key)

    def generate(
        self,
        alert: CompoundAlert,
        sensor_readings: list[SensorReading],
        permits: list[PermitRecord],
    ) -> IncidentReportDraft:
        evidence_ids = [alert.alert_id]
        if alert.evidence_hash:
            evidence_ids.append(alert.evidence_hash)

        bundle = self.ledger.export_evidence_bundle(evidence_ids)
        bundle_hash = bundle.get("merkle_root", "")

        sections = self._generate_sections(
            alert, sensor_readings, permits, bundle
        )

        timeline = self._build_timeline(alert, sensor_readings, permits)

        return IncidentReportDraft(
            report_id=str(uuid4()),
            alert_id=alert.alert_id,
            generated_at=datetime.now(timezone.utc),
            regulatory_format="DGFASLI/OISD Preliminary Incident Report",
            sections=sections,
            evidence_bundle_hash=bundle_hash,
            sensor_readings=sensor_readings,
            permits=permits,
            timeline=timeline,
        )

    def _generate_sections(
        self,
        alert: CompoundAlert,
        sensors: list[SensorReading],
        permits: list[PermitRecord],
        bundle: dict[str, Any],
    ) -> dict[str, str]:
        if self._client:
            try:
                return self._llm_generate(alert, sensors, permits, bundle)
            except Exception:
                pass

        return self._template_generate(alert, sensors, permits, bundle)

    def _llm_generate(
        self,
        alert: CompoundAlert,
        sensors: list[SensorReading],
        permits: list[PermitRecord],
        bundle: dict[str, Any],
    ) -> dict[str, str]:
        context = {
            "alert": alert.model_dump(mode="json"),
            "sensors": [s.model_dump(mode="json") for s in sensors],
            "permits": [p.model_dump(mode="json") for p in permits],
            "evidence_chain_valid": bundle.get("chain_valid"),
            "merkle_root": bundle.get("merkle_root"),
        }

        response = self._client.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=2000,
            system=(
                "Generate a preliminary regulatory incident report in JSON format with these sections: "
                "incident_summary, immediate_actions_taken, affected_zones_and_equipment, "
                "sensor_data_summary, permit_status_at_time, causal_analysis, "
                "regulatory_notifications_required, evidence_chain_reference, recommended_follow_up. "
                "Reference specific sensor IDs, permit IDs, timestamps, and measurements. "
                "Format for DGFASLI/OISD reporting standards."
            ),
            messages=[
                {
                    "role": "user",
                    "content": f"Generate incident report:\n{json.dumps(context, indent=2, default=str)}",
                }
            ],
        )

        text = response.content[0].text
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return self._template_generate(alert, sensors, permits, bundle)

    def _template_generate(
        self,
        alert: CompoundAlert,
        sensors: list[SensorReading],
        permits: list[PermitRecord],
        bundle: dict[str, Any],
    ) -> dict[str, str]:
        relevant_permits = [
            p for p in permits if p.permit_id in alert.permit_ids
        ] or permits

        sensor_summary = []
        for s in sensors:
            ratio = s.value_ppm / s.baseline_ppm if s.baseline_ppm > 0 else 0
            sensor_summary.append(
                f"{s.sensor_id} ({s.gas_type}): {s.value_ppm} ppm "
                f"({ratio:.1f}x baseline) in {s.zone_id} at {s.timestamp.isoformat()}"
            )

        permit_summary = []
        for p in relevant_permits:
            permit_summary.append(
                f"{p.permit_id} ({p.permit_type.value}): {p.status.value} in "
                f"{p.zone_id}, {p.start_time.isoformat()} to {p.end_time.isoformat()}"
            )

        return {
            "incident_summary": (
                f"Compound risk alert {alert.alert_id} — {alert.severity.value.upper()} severity "
                f"in {alert.zone_id}. Pattern: {alert.hazard_pattern_id}. "
                f"Confidence: {alert.confidence:.0%}. {alert.explanation}"
            ),
            "immediate_actions_taken": "\n".join(
                f"- {action}" for action in alert.recommended_actions
            ),
            "affected_zones_and_equipment": (
                f"Primary zone: {alert.zone_id}. "
                f"Sensors: {', '.join(alert.sensor_ids) or 'N/A'}. "
                f"Permits: {', '.join(alert.permit_ids) or 'N/A'}."
            ),
            "sensor_data_summary": "\n".join(sensor_summary) or "No sensor data available.",
            "permit_status_at_time": "\n".join(permit_summary) or "No active permits.",
            "causal_analysis": alert.explanation,
            "regulatory_notifications_required": (
                "Notify plant safety head immediately. "
                "DGFASLI Form IV reporting required if incident confirmed. "
                "OISD incident notification per plant safety manual."
            ),
            "evidence_chain_reference": (
                f"Evidence chain valid: {bundle.get('chain_valid', 'unknown')}. "
                f"Merkle root: {bundle.get('merkle_root', 'N/A')}. "
                f"Alert evidence hash: {alert.evidence_hash or 'N/A'}."
            ),
            "recommended_follow_up": (
                "Conduct formal investigation. Preserve all sensor logs and permit records. "
                "Review and update causal risk graph if new patterns identified. "
                "Submit trust calibration feedback on alert accuracy."
            ),
        }

    def _build_timeline(
        self,
        alert: CompoundAlert,
        sensors: list[SensorReading],
        permits: list[PermitRecord],
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []

        for s in sensors:
            events.append(
                {
                    "timestamp": s.timestamp.isoformat(),
                    "type": "sensor_reading",
                    "description": f"{s.sensor_id}: {s.value_ppm} ppm {s.gas_type}",
                }
            )

        for p in permits:
            events.append(
                {
                    "timestamp": p.start_time.isoformat(),
                    "type": "permit_active",
                    "description": f"{p.permit_id}: {p.permit_type.value} in {p.zone_id}",
                }
            )

        events.append(
            {
                "timestamp": alert.timestamp.isoformat(),
                "type": "compound_alert",
                "description": f"Alert {alert.alert_id}: {alert.hazard_pattern_id}",
            }
        )

        events.sort(key=lambda e: e["timestamp"])
        return events
