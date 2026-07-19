"""Reports, RAG, compliance, voice, and simulation API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from backend.api.schemas import (
    ComplianceAuditRequest,
    ComplianceAuditResponse,
    ComplianceGap,
    AlertSeverity,
    RAGQueryRequest,
    RAGQueryResponse,
    VoiceReportRequest,
    VoiceReportResponse,
    SimulationControlRequest,
    SimulationState,
    EvidenceRecord,
)
from backend.evidence_ledger.ledger_store import get_ledger
from backend.rag.retriever import get_retriever
from data.simulation.engine import get_simulation_engine

router = APIRouter(tags=["reports"])


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest):
    retriever = get_retriever()
    alert_context = None
    if request.alert_id:
        from backend.agents.orchestrator import get_orchestrator
        alert = get_orchestrator().get_alert_by_id(request.alert_id)
        if alert:
            alert_context = alert.model_dump(mode="json")
    return retriever.query(request.query, top_k=request.top_k, alert_context=alert_context)


@router.post("/compliance/audit", response_model=ComplianceAuditResponse)
async def compliance_audit(request: ComplianceAuditRequest):
    retriever = get_retriever()
    result = retriever.audit_compliance(request.document_text, request.applicable_frameworks)

    gaps = [
        ComplianceGap(
            gap_id=g["gap_id"],
            severity=AlertSeverity(g.get("severity", "medium")),
            description=g["description"],
            regulatory_clause=g["regulatory_clause"],
            framework=g["framework"],
            recommendation=g["recommendation"],
        )
        for g in result["gaps"]
    ]

    return ComplianceAuditResponse(
        document_type=request.document_type,
        gaps=gaps,
        compliance_score=result["compliance_score"],
        summary=result["summary"],
    )


@router.post("/voice/report", response_model=VoiceReportResponse)
async def voice_report(request: VoiceReportRequest):
    transcript = request.transcript.lower()

    severity = AlertSeverity.MEDIUM
    classification = "near_miss"

    hazard_keywords = {
        "gas": ("gas_leak", AlertSeverity.HIGH),
        "leak": ("gas_leak", AlertSeverity.HIGH),
        "fire": ("fire_hazard", AlertSeverity.CRITICAL),
        "aag": ("fire_hazard", AlertSeverity.CRITICAL),
        "गैस": ("gas_leak", AlertSeverity.HIGH),
        "ఎగురు": ("gas_leak", AlertSeverity.HIGH),
        "ಸ್ಫೋಟ": ("explosion_risk", AlertSeverity.CRITICAL),
        "danger": ("general_hazard", AlertSeverity.MEDIUM),
        "खतरा": ("general_hazard", AlertSeverity.MEDIUM),
        "పరిస్థితి": ("general_hazard", AlertSeverity.MEDIUM),
    }

    for keyword, (cls, sev) in hazard_keywords.items():
        if keyword in transcript:
            classification = cls
            severity = sev
            break

    report_id = f"VR-{uuid4().hex[:8]}"
    structured = {
        "report_id": report_id,
        "transcript": request.transcript,
        "language": request.language,
        "classification": classification,
        "severity": severity.value,
        "reporter_zone": request.reporter_zone,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    ledger = get_ledger()
    ledger.record("voice_report", structured, record_id=report_id)

    lang_messages = {
        "hi": "आपकी रिपोर्ट दर्ज कर ली गई है। सुरक्षा अधिकारी को सूचित किया जाएगा।",
        "te": "మీ నివేదిక నమోదు చేయబడింది. భద్రతా అధికారికి తెలియజేస్తాము.",
        "kn": "ನಿಮ್ಮ ವರದಿಯನ್ನು ದಾಖಲಿಸಲಾಗಿದೆ. ಸುರಕ್ಷತಾ ಅಧಿಕಾರಿಗೆ ತಿಳಿಸWill be notified.",
        "en": "Your report has been recorded. The safety officer will be notified.",
    }

    return VoiceReportResponse(
        report_id=report_id,
        classification=classification,
        severity=severity,
        structured_record=structured,
        routed_to_corpus=True,
        acknowledgment_message=lang_messages.get(request.language, lang_messages["en"]),
    )


@router.post("/simulation/control", response_model=SimulationState)
async def simulation_control(request: SimulationControlRequest):
    engine = get_simulation_engine()

    if request.action == "start":
        return engine.start()
    elif request.action == "stop":
        return engine.stop()
    elif request.action == "reset":
        engine.reset()
        return engine.state
    elif request.action == "step":
        engine.step()
        return engine.state

    return engine.state


@router.get("/simulation/state", response_model=SimulationState)
async def simulation_state():
    engine = get_simulation_engine()
    return engine.state


@router.post("/simulation/step")
async def simulation_step():
    engine = get_simulation_engine()
    return engine.step()


@router.get("/evidence", response_model=list[EvidenceRecord])
async def list_evidence(limit: int = 50, record_type: str | None = None):
    ledger = get_ledger()
    entries = ledger.get_records(record_type, limit)
    return [
        EvidenceRecord(
            record_id=e.record_id,
            timestamp=e.timestamp,
            record_type=e.record_type,
            payload_hash=e.payload_hash,
            merkle_root=e.merkle_root,
            previous_hash=e.previous_hash,
            sequence_number=e.sequence_number,
        )
        for e in entries
    ]


@router.get("/evidence/verify")
async def verify_evidence():
    ledger = get_ledger()
    valid, errors = ledger.verify()
    return {
        "chain_valid": valid,
        "errors": errors,
        "merkle_root": ledger.merkle_root,
        "record_count": len(ledger.get_records()),
    }
