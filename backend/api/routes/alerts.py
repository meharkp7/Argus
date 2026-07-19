"""Alert API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.agents.orchestrator import get_orchestrator
from backend.api.schemas import CompoundAlert, RAGQueryRequest, RAGQueryResponse
from backend.rag.retriever import get_retriever
from backend.response_orchestrator.playbooks import PlaybookEngine
from backend.response_orchestrator.report_generator import IncidentReportGenerator
from data.simulation.engine import get_simulation_engine

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/", response_model=list[CompoundAlert])
async def list_alerts(limit: int = 20):
    orchestrator = get_orchestrator()
    return orchestrator.get_recent_alerts(limit)


@router.get("/{alert_id}", response_model=CompoundAlert)
async def get_alert(alert_id: str):
    orchestrator = get_orchestrator()
    alert = orchestrator.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/investigate", response_model=RAGQueryResponse)
async def investigate_alert(alert_id: str, request: RAGQueryRequest | None = None):
    orchestrator = get_orchestrator()
    alert = orchestrator.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    query = request.query if request else f"What past incidents resemble this alert: {alert.explanation}"
    retriever = get_retriever()
    return retriever.query(
        query,
        top_k=request.top_k if request else 5,
        alert_context=alert.model_dump(mode="json"),
    )


@router.post("/{alert_id}/emergency-response")
async def trigger_emergency(alert_id: str, operator_confirmed: bool = False):
    orchestrator = get_orchestrator()
    alert = orchestrator.get_alert_by_id(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    playbook = PlaybookEngine()
    actions = playbook.execute(alert, operator_confirmed)

    engine = get_simulation_engine()
    readings = engine.get_current_readings()
    sensor_readings = engine.sensor_gen._generate_readings() if hasattr(engine.sensor_gen, '_generate_readings') else []
    permits = engine.permit_gen.get_active_permits()

    report_gen = IncidentReportGenerator()
    report = report_gen.generate(alert, sensor_readings, permits)

    return {
        "response_id": f"RESP-{alert_id[:8]}",
        "alert_id": alert_id,
        "actions": [a.model_dump(mode="json") for a in actions],
        "incident_report": report.model_dump(mode="json"),
        "evidence_preserved": True,
    }
