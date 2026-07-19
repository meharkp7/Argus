"""Geospatial heatmap API routes."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.agents.orchestrator import get_orchestrator
from backend.api.schemas import (
    HeatmapResponse,
    PlantInfrastructure,
    SensorPoint,
    ZoneRiskScore,
)
from backend.config.settings import PLANT_LAYOUT_PATH
from backend.risk_graph.geometry import normalize_polygon_geometry
from backend.risk_graph.scoring import score_zone_risk
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


def _sensor_status(ratio: float) -> str:
    if ratio >= 2.5:
        return "critical"
    if ratio >= 1.5:
        return "elevated"
    return "normal"


def _build_zone_sensors(zone_id: str, sensor_readings, zone_sensor_ids: list[str]) -> list[dict]:
    snapshots = []
    for reading in sensor_readings:
        if reading.zone_id != zone_id and reading.sensor_id not in zone_sensor_ids:
            continue
        ratio = reading.value_ppm / reading.baseline_ppm if reading.baseline_ppm > 0 else 1.0
        snapshots.append({
            "sensor_id": reading.sensor_id,
            "gas_type": reading.gas_type,
            "value_ppm": round(reading.value_ppm, 2),
            "baseline_ppm": round(reading.baseline_ppm, 2),
            "ratio": round(ratio, 2),
            "status": _sensor_status(ratio),
            "unit": reading.unit,
        })
    return snapshots


@router.get("/", response_model=HeatmapResponse)
async def get_heatmap():
    engine = get_simulation_engine()
    sensor_readings = engine.sensor_gen._generate_readings()
    permits = engine.permit_gen.get_active_permits()
    weather = engine.weather_feed.tick()
    shifts = engine._get_active_shifts()

    with open(PLANT_LAYOUT_PATH, encoding="utf-8") as f:
        plant_map = json.load(f)

    metadata = plant_map.get("metadata", {})
    reading_by_id = {r.sensor_id: r for r in sensor_readings}
    shift_by_zone = {s.zone_id: s.crew_name for s in shifts}

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

    zones: list[ZoneRiskScore] = []
    infrastructure: list[PlantInfrastructure] = []
    sensor_points: list[SensorPoint] = []
    all_lats, all_lons = [], []

    for feature in plant_map["features"]:
        props = feature["properties"]
        geom = feature["geometry"]
        feature_type = props.get("feature_type", "zone")

        if feature_type in {"pipeline", "road", "boundary"}:
            infrastructure.append(
                PlantInfrastructure(
                    name=props.get("name", feature_type),
                    feature_type=feature_type,
                    geometry=geom,
                    properties=props,
                )
            )
            if geom["type"] == "LineString":
                for lon, lat in geom["coordinates"]:
                    all_lats.append(lat)
                    all_lons.append(lon)
            continue

        if feature_type == "sensor":
            lon, lat = geom["coordinates"]
            reading = reading_by_id.get(props["sensor_id"])
            ratio = 1.0
            status = "normal"
            value_ppm = None
            baseline_ppm = None
            if reading:
                value_ppm = round(reading.value_ppm, 2)
                baseline_ppm = round(reading.baseline_ppm, 2)
                ratio = reading.value_ppm / reading.baseline_ppm if reading.baseline_ppm > 0 else 1.0
                status = _sensor_status(ratio)
            sensor_points.append(
                SensorPoint(
                    sensor_id=props["sensor_id"],
                    zone_id=props["zone_id"],
                    gas_type=props["gas_type"],
                    label=props.get("label", props["sensor_id"]),
                    latitude=lat,
                    longitude=lon,
                    value_ppm=value_ppm,
                    baseline_ppm=baseline_ppm,
                    status=status,
                )
            )
            all_lats.append(lat)
            all_lons.append(lon)
            continue

        zone_id = props["zone_id"]
        coords = geom["coordinates"][0]
        lats = [c[1] for c in coords]
        lons = [c[0] for c in coords]
        centroid = [sum(lons) / len(lons), sum(lats) / len(lats)]
        all_lats.extend(lats)
        all_lons.extend(lons)

        zone_permits = [p for p in permits if p.zone_id == zone_id]
        zone_sensor_ids = props.get("sensors", [])
        zone_readings = [r for r in sensor_readings if r.zone_id == zone_id or r.sensor_id in zone_sensor_ids]
        zone_anomalies = sum(
            1 for s in zone_readings
            if s.baseline_ppm > 0 and (s.value_ppm / s.baseline_ppm) >= 1.5
        )

        scoring = score_zone_risk(
            zone_id=zone_id,
            hazard_matches=hazard_matches,
            permits=zone_permits,
            sensor_readings=zone_readings,
            zone_properties=props,
            maintenance_status=engine._maintenance,
            shifts=shifts,
            weather=weather,
        )

        explanation = None
        for match in hazard_matches:
            if match.zone_id == zone_id:
                explanation = match.pattern.description
                break

        normalized_geometry = normalize_polygon_geometry(geom)

        zones.append(
            ZoneRiskScore(
                zone_id=zone_id,
                zone_name=props["name"],
                risk_score=scoring["risk_score"],
                risk_level=scoring["risk_level"],
                active_permits=scoring["active_permit_count"],
                sensor_anomalies=scoring["sensor_anomaly_count"],
                explanation=explanation,
                centroid=centroid,
                geometry=normalized_geometry,
                hazard_class=props.get("hazard_class"),
                max_occupancy=props.get("max_occupancy"),
                area_sqm=props.get("area_sqm"),
                maintenance_status=engine._maintenance.get(zone_id, "unknown"),
                process_units=props.get("process_units", []),
                sensors=_build_zone_sensors(zone_id, sensor_readings, zone_sensor_ids),
                active_shift=shift_by_zone.get(zone_id),
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
        weather=weather,
        plant_name=metadata.get("name"),
        plant_location=metadata.get("location"),
        infrastructure=infrastructure,
        sensor_points=sensor_points,
    )


@router.get("/layout")
async def get_plant_layout():
    with open(PLANT_LAYOUT_PATH, encoding="utf-8") as f:
        return json.load(f)
