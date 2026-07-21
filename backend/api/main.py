"""ARGUS FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import alerts, feedback, heatmap, permits, reports
from backend.api.schemas import HealthResponse
from backend.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="ARGUS — Zero-Harm Intelligence Layer for Indian Heavy Industry",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(alerts.router, prefix="/api")
    app.include_router(permits.router, prefix="/api")
    app.include_router(heatmap.router, prefix="/api")
    app.include_router(feedback.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")

    @app.get("/api/health", response_model=HealthResponse)
    async def health():
        from backend.evidence_ledger.ledger_store import get_ledger
        from data.simulation.engine import _engine as engine_instance

        ledger = get_ledger()
        valid, _ = ledger.verify()

        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            components={
                "api": "operational",
                "evidence_ledger": "valid" if valid else "integrity_warning",
                "simulation": "running" if engine_instance and engine_instance._running else "idle",
                "rag_corpus": "lazy_loaded",
            },
        )

    return app


app = create_app()
