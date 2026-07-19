"""Shared request/response models — the API contract boundary."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConfidenceBand(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FeedbackLabel(str, Enum):
    USEFUL = "useful"
    NOT_USEFUL = "not_useful"
    FALSE_ALARM = "false_alarm"


class PermitType(str, Enum):
    HOT_WORK = "hot_work"
    CONFINED_SPACE = "confined_space"
    LIFTING = "lifting"
    ELECTRICAL = "electrical"
    EXCAVATION = "excavation"


class PermitStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    ACTIVE = "active"
    COMPLETED = "completed"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class SensorReading(BaseModel):
    sensor_id: str
    zone_id: str
    timestamp: datetime
    gas_type: str
    value_ppm: float
    baseline_ppm: float
    unit: str = "ppm"
    latitude: float | None = None
    longitude: float | None = None


class PermitRecord(BaseModel):
    permit_id: str
    permit_type: PermitType
    zone_id: str
    status: PermitStatus
    requested_at: datetime
    approved_at: datetime | None = None
    start_time: datetime
    end_time: datetime
    requester: str
    approver: str | None = None
    description: str
    latitude: float
    longitude: float


class ShiftRecord(BaseModel):
    shift_id: str
    zone_id: str
    crew_name: str
    start_time: datetime
    end_time: datetime
    overtime_hours: float = 0.0
    is_night_shift: bool = False
    contractor_ratio: float = 0.0
    experience_level: str = "standard"


class WeatherReading(BaseModel):
    timestamp: datetime
    wind_speed_ms: float
    wind_direction_deg: float
    temperature_c: float
    humidity_pct: float


class CausalChainLink(BaseModel):
    node_id: str
    label: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    weight: float = 1.0


class CompoundAlert(BaseModel):
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    confidence: float
    confidence_band: ConfidenceBand
    zone_id: str
    hazard_pattern_id: str
    causal_chain: list[CausalChainLink]
    explanation: str
    recommended_actions: list[str]
    lead_time_minutes: float | None = None
    sensor_ids: list[str] = Field(default_factory=list)
    permit_ids: list[str] = Field(default_factory=list)
    baseline_would_trigger: bool = False
    evidence_hash: str | None = None


class AlertFeedback(BaseModel):
    alert_id: str
    label: FeedbackLabel
    operator_id: str
    comment: str | None = None
    timestamp: datetime | None = None


class TrustCalibrationMetrics(BaseModel):
    total_alerts: int
    feedback_count: int
    false_positive_rate: float
    precision: float
    threshold_adjustments: list[dict[str, Any]]
    history: list[dict[str, Any]]


class ZoneRiskScore(BaseModel):
    zone_id: str
    zone_name: str
    risk_score: float
    risk_level: str
    active_permits: int
    sensor_anomalies: int
    explanation: str | None = None
    centroid: list[float]
    geometry: dict[str, Any] | None = None


class HeatmapResponse(BaseModel):
    timestamp: datetime
    zones: list[ZoneRiskScore]
    active_alerts: list[str]
    plant_bounds: dict[str, float]


class PermitPreMortemRequest(BaseModel):
    permit_type: PermitType
    zone_id: str
    start_time: datetime
    end_time: datetime
    description: str
    requester: str
    latitude: float
    longitude: float


class PermitPreMortemResponse(BaseModel):
    approved_recommendation: bool
    risk_score: float
    confidence: float
    violations: list[str]
    warnings: list[str]
    reasoning: str
    causal_factors: list[CausalChainLink]
    regulatory_citations: list[str] = Field(default_factory=list)


class PermitSubmission(PermitPreMortemRequest):
    pass


class RAGQueryRequest(BaseModel):
    query: str
    alert_id: str | None = None
    top_k: int = 5


class RAGCitation(BaseModel):
    document_id: str
    title: str
    source: str
    excerpt: str
    relevance_score: float
    clause_reference: str | None = None


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    citations: list[RAGCitation]
    matched_patterns: list[str]


class VoiceReportRequest(BaseModel):
    transcript: str
    language: str = "hi"
    reporter_zone: str | None = None
    audio_duration_seconds: float | None = None


class VoiceReportResponse(BaseModel):
    report_id: str
    classification: str
    severity: AlertSeverity
    structured_record: dict[str, Any]
    routed_to_corpus: bool
    acknowledgment_message: str


class ComplianceAuditRequest(BaseModel):
    document_text: str
    document_type: str = "procedure"
    applicable_frameworks: list[str] = Field(
        default_factory=lambda: ["OISD", "DGMS", "Factory Act"]
    )


class ComplianceGap(BaseModel):
    gap_id: str
    severity: AlertSeverity
    description: str
    regulatory_clause: str
    framework: str
    recommendation: str


class ComplianceAuditResponse(BaseModel):
    document_type: str
    gaps: list[ComplianceGap]
    compliance_score: float
    summary: str


class EmergencyTriggerRequest(BaseModel):
    alert_id: str
    operator_confirmed: bool = False
    operator_id: str


class EmergencyAction(BaseModel):
    step_id: str
    action: str
    channel: str
    status: str
    timestamp: datetime


class IncidentReportDraft(BaseModel):
    report_id: str
    alert_id: str
    generated_at: datetime
    regulatory_format: str
    sections: dict[str, str]
    evidence_bundle_hash: str
    sensor_readings: list[SensorReading]
    permits: list[PermitRecord]
    timeline: list[dict[str, Any]]


class EmergencyResponseResult(BaseModel):
    response_id: str
    alert_id: str
    actions: list[EmergencyAction]
    incident_report: IncidentReportDraft
    evidence_preserved: bool


class SimulationState(BaseModel):
    running: bool
    scenario_id: str | None
    current_tick: int
    total_ticks: int
    elapsed_seconds: float
    last_alert_id: str | None = None


class SimulationControlRequest(BaseModel):
    action: str
    scenario_id: str | None = "compound_risk_scenario"


class EvidenceRecord(BaseModel):
    record_id: str
    timestamp: datetime
    record_type: str
    payload_hash: str
    merkle_root: str
    previous_hash: str
    sequence_number: int


class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict[str, str]
