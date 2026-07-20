"""ARGUS FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import alerts, feedback, heatmap, permits, reports
from backend.api.schemas import HealthResponse
from backend.config.settings import get_settings
from backend.rag.ingest import CorpusIngester
from data.simulation.engine import get_simulation_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    ingester = CorpusIngester()
    doc_count = ingester.ingest_all()
    print(f"ARGUS: Indexed {doc_count} corpus documents")

    engine = get_simulation_engine()
    engine.start()

    simulation_task = asyncio.create_task(_simulation_loop(engine, settings.simulation_tick_interval_seconds))

    try:
        yield
    finally:
        simulation_task.cancel()
        try:
            await simulation_task
        except asyncio.CancelledError:
            pass
        engine.stop()


async def _simulation_loop(engine: Any, interval: float):
    while True:
        try:
            if engine._running:
                engine.step()
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            print(f"Simulation loop error: {exc}")
            await asyncio.sleep(interval)


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

        ledger = get_ledger()
        valid, _ = ledger.verify()

        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            components={
                "api": "operational",
                "evidence_ledger": "valid" if valid else "integrity_warning",
                "simulation": "running" if get_simulation_engine()._running else "stopped",
                "rag_corpus": "loaded",
            },
        )

    return app


app = create_app()
