"""Multi-agent orchestrator coordinating the compound risk detection pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.agents.correlation_agent import CorrelationAgent, CorrelationResult
from backend.agents.explainer_agent import ExplainerAgent
from backend.agents.permit_agent import PermitAgent
from backend.agents.sensor_agent import SensorAgent
from backend.api.schemas import (
    CompoundAlert,
    PermitRecord,
    SensorReading,
    ShiftRecord,
    WeatherReading,
)
from backend.evidence_ledger.ledger_store import get_ledger
from backend.trust_calibration.feedback_store import get_feedback_store


class AgentOrchestrator:
    """Coordinates Sensor, Permit, Correlation, and Explainer agents."""

    def __init__(self) -> None:
        self.sensor_agent = SensorAgent()
        self.permit_agent = PermitAgent()
        self.correlation_agent = CorrelationAgent()
        self.explainer_agent = ExplainerAgent()
        self.ledger = get_ledger()
        self.feedback_store = get_feedback_store()
        self._alert_history: list[CompoundAlert] = []

    @property
    def alert_history(self) -> list[CompoundAlert]:
        return self._alert_history

    def process_tick(
        self,
        sensor_readings: list[SensorReading],
        permits: list[PermitRecord],
        shifts: list[ShiftRecord],
        weather: WeatherReading | None = None,
        maintenance_status: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        for reading in sensor_readings:
            self.ledger.record(
                "sensor_reading",
                reading.model_dump(mode="json"),
                record_id=f"sensor-{reading.sensor_id}-{reading.timestamp.isoformat()}",
                timestamp=reading.timestamp,
            )

        sensor_anomalies = self.sensor_agent.analyze(sensor_readings)
        baseline_triggered = self.sensor_agent.baseline_would_trigger(sensor_readings)
        permit_analyses = self.permit_agent.analyze_permits(permits)

        correlation_result = self.correlation_agent.correlate(
            sensor_readings=sensor_readings,
            sensor_anomalies=sensor_anomalies,
            permit_analyses=permit_analyses,
            permits=permits,
            shifts=shifts,
            weather=weather,
            baseline_would_trigger=baseline_triggered,
            maintenance_status=maintenance_status,
        )

        explained_alerts: list[CompoundAlert] = []
        for alert in correlation_result.alerts:
            alert.explanation = self.explainer_agent.explain(alert)

            evidence_entry = self.ledger.record(
                "compound_alert",
                alert.model_dump(mode="json"),
                record_id=alert.alert_id,
                timestamp=alert.timestamp,
            )
            alert.evidence_hash = evidence_entry.entry_hash

            self.feedback_store.record_alert(
                alert.alert_id,
                alert.severity.value,
                alert.confidence,
                alert.timestamp,
            )

            explained_alerts.append(alert)
            self._alert_history.append(alert)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sensor_anomalies": [
                {
                    "sensor_id": a.sensor_id,
                    "zone_id": a.zone_id,
                    "severity": a.severity,
                    "ratio": a.ratio_to_baseline,
                    "z_score": a.z_score,
                }
                for a in sensor_anomalies
            ],
            "permit_analyses": [
                {
                    "permit_id": p.permit_id,
                    "risk_score": p.risk_score,
                    "flags": p.risk_flags,
                    "violations": p.violations,
                }
                for p in permit_analyses
            ],
            "alerts": explained_alerts,
            "hazard_matches": len(correlation_result.hazard_matches),
            "baseline_would_trigger": baseline_triggered,
            "compound_alert_fired": len(explained_alerts) > 0,
        }

    def get_recent_alerts(self, limit: int = 20) -> list[CompoundAlert]:
        return self._alert_history[-limit:]

    def get_alert_by_id(self, alert_id: str) -> CompoundAlert | None:
        for alert in reversed(self._alert_history):
            if alert.alert_id == alert_id:
                return alert
        return None


_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
