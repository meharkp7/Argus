"""Geospatial heatmap API routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter

from backend.agents.orchestrator import get_orchestrator
from backend.api.schemas import HeatmapResponse, ZoneRiskScore
from backend.config.settings import PLANT_LAYOUT_PATH
from backend.risk_graph.traversal import GraphTraverser, PlantState
from data.simulation.engine import get_simulation_engine

router = APIRouter(prefix="/heatmap", tags=["heatmap"])


def _risk_level(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.4:
        return "medium"
    if score >= 0.2:
        return "low"
    return "normal"


def _risk_color(level: str) -> str:
    return {
        "critical": "#DC2626",
        "high": "#EA580C",
        "medium": "#CA8A04",
        "low": "#65A30D",
        "normal": "#16A34A",
    }.get(level, "#16A34A")


@router.get("/", response_model=HeatmapResponse)
async def get_heatmap():
    engine = get_simulation_engine()
    readings = engine.get_current_readings()

    with open(PLANT_LAYOUT_PATH, encoding="utf-8") as f:
        plant_map = json.load(f)

    sensor_readings = engine.sensor_gen._generate_readings()
    permits = engine.permit_gen.get_active_permits()
    weather = engine.weather_feed.tick()
    shifts = engine._get_active_shifts()

    state = PlantState(
        sensors=sensor_readings,
        permits=permits,
        shifts=shifts,
        weather=weather,
        timestamp=datetime.now(timezone.utc),
        maintenance_status=engine._maintenance,
    )

    traverser = GraphTraverser()
    hazard_matches = traverser.match_hazards(state)

    orchestrator = get_orchestrator()
    recent_alerts = orchestrator.get_recent_alerts(5)
    alert_zones = {a.zone_id for a in recent_alerts}

    zones: list[ZoneRiskScore] = []
    all_lats, all_lons = [], []

    for feature in plant_map["features"]:
        props = feature["properties"]
        zone_id = props["zone_id"]
        coords = feature["geometry"]["coordinates"][0]
        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        centroid = [sum(lons) / len(lons), sum(lats) / len(lats)]
        all_lats.extend(lats)
        all_lons.extend(lons)

        zone_score = 0.1
        for match in hazard_matches:
            if match.zone_id == zone_id:
                zone_score = max(zone_score, match.score)

        zone_permits = [p for p in permits if p.zone_id == zone_id]
        zone_anomalies = sum(
            1 for s in sensor_readings
            if s.zone_id == zone_id and s.baseline_ppm > 0
            and (s.value_ppm / s.baseline_ppm) >= 1.5
        )

        if zone_anomalies > 0:
            zone_score = max(zone_score, 0.3 + zone_anomalies * 0.15)
        if len(zone_permits) > 0:
            zone_score = max(zone_score, 0.2 + len(zone_permits) * 0.1)

        level = _risk_level(zone_score)
        explanation = None
        for match in hazard_matches:
            if match.zone_id == zone_id:
                explanation = match.pattern.description
                break

        zones.append(
            ZoneRiskScore(
                zone_id=zone_id,
                zone_name=props["name"],
                risk_score=round(min(zone_score, 1.0), 3),
                risk_level=level,
                active_permits=len(zone_permits),
                sensor_anomalies=zone_anomalies,
                explanation=explanation,
                centroid=centroid,
                geometry=feature["geometry"],
            )
        )

    return HeatmapResponse(
        timestamp=datetime.now(timezone.utc),
        zones=zones,
        active_alerts=[a.alert_id for a in recent_alerts],
        plant_bounds={
            "min_lat": min(all_lats) if all_lats else 0,
            "max_lat": max(all_lats) if all_lats else 0,
            "min_lon": min(all_lons) if all_lons else 0,
            "max_lon": max(all_lons) if all_lons else 0,
        },
    )


@router.get("/layout")
async def get_plant_layout():
    with open(PLANT_LAYOUT_PATH, encoding="utf-8") as f:
        return json.load(f)
