"""Trust calibration and feedback API routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.api.schemas import AlertFeedback, TrustCalibrationMetrics
from backend.trust_calibration.feedback_store import get_feedback_store
from backend.trust_calibration.threshold_updater import get_threshold_updater

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/", response_model=AlertFeedback)
async def submit_feedback(feedback: AlertFeedback):
    store = get_feedback_store()
    result = store.submit_feedback(feedback)

    updater = get_threshold_updater()
    updater.update_thresholds()

    return result


@router.get("/metrics", response_model=TrustCalibrationMetrics)
async def get_metrics():
    store = get_feedback_store()
    return store.compute_metrics()


@router.get("/thresholds")
async def get_thresholds():
    updater = get_threshold_updater()
    return updater.get_current_thresholds()
