"""Permit API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from backend.api.schemas import (
    PermitPreMortemRequest,
    PermitPreMortemResponse,
    PermitRecord,
    PermitStatus,
    PermitSubmission,
)
from backend.evidence_ledger.ledger_store import get_ledger
from backend.permit_engine.pre_mortem import PreMortemSimulator
from data.simulation.engine import get_simulation_engine

router = APIRouter(prefix="/permits", tags=["permits"])


@router.get("/")
async def list_permits():
    engine = get_simulation_engine()
    return engine.permit_gen.get_active_permits()


@router.post("/pre-mortem", response_model=PermitPreMortemResponse)
async def pre_mortem(request: PermitPreMortemRequest):
    engine = get_simulation_engine()
    simulator = PreMortemSimulator()

    sensor_readings = engine.sensor_gen._generate_readings()
    permits = engine.permit_gen.get_active_permits()
    weather = engine.weather_feed.tick()
    shifts = engine._get_active_shifts()

    result = simulator.simulate(
        request, permits, sensor_readings, shifts, weather
    )

    ledger = get_ledger()
    ledger.record(
        "pre_mortem_simulation",
        {"request": request.model_dump(mode="json"), "result": result.model_dump(mode="json")},
        record_id=f"pm-{uuid4().hex[:8]}",
    )

    return result


@router.post("/submit", response_model=PermitPreMortemResponse)
async def submit_permit(submission: PermitSubmission):
    engine = get_simulation_engine()
    simulator = PreMortemSimulator()

    sensor_readings = engine.sensor_gen._generate_readings()
    permits = engine.permit_gen.get_active_permits()
    weather = engine.weather_feed.tick()
    shifts = engine._get_active_shifts()

    pre_mortem_result = simulator.simulate(
        submission, permits, sensor_readings, shifts, weather
    )

    if pre_mortem_result.approved_recommendation:
        permit = PermitRecord(
            permit_id=f"HW-{uuid4().hex[:6].upper()}",
            permit_type=submission.permit_type,
            zone_id=submission.zone_id,
            status=PermitStatus.ACTIVE,
            requested_at=datetime.now(timezone.utc),
            approved_at=datetime.now(timezone.utc),
            start_time=submission.start_time,
            end_time=submission.end_time,
            requester=submission.requester,
            approver="ARGUS Pre-Mortem Approved",
            description=submission.description,
            latitude=submission.latitude,
            longitude=submission.longitude,
        )
        engine.permit_gen.add_permit(permit)

        ledger = get_ledger()
        ledger.record("permit_approved", permit.model_dump(mode="json"), record_id=permit.permit_id)

    return pre_mortem_result
