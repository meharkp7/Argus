"""Risk scoring utilities for zone-level hazard assessment."""

from __future__ import annotations

from typing import Any


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def score_zone_risk(
    *,
    zone_id: str,
    hazard_matches: list[Any],
    permits: list[Any],
    sensor_readings: list[Any],
    zone_properties: dict[str, Any] | None = None,
    maintenance_status: dict[str, str] | None = None,
    shifts: list[Any] | None = None,
    weather: Any = None,
) -> dict[str, Any]:
    """Compute a calibrated, explainable risk score for a zone."""

    zone_properties = zone_properties or {}
    maintenance_status = maintenance_status or {}
    shifts = shifts or []

    base_match_score = max((match.score for match in hazard_matches if getattr(match, "zone_id", None) == zone_id), default=0.1)
    active_permits = [permit for permit in permits if getattr(permit.status, "value", None) in {"active", "approved"} and getattr(permit, "zone_id", None) == zone_id]

    zone_sensor_readings = [reading for reading in sensor_readings if getattr(reading, "zone_id", None) == zone_id]
    ratios = []
    anomaly_count = 0
    for reading in zone_sensor_readings:
        baseline = getattr(reading, "baseline_ppm", 0.0) or 0.0
        if baseline <= 0:
            ratio = 1.0
        else:
            ratio = float(getattr(reading, "value_ppm", 0.0) or 0.0) / baseline
        ratios.append(ratio)
        if ratio >= 1.5:
            anomaly_count += 1

    max_ratio = max(ratios, default=1.0)
    permit_pressure = min(0.25, 0.05 * len(active_permits))
    sensor_pressure = min(0.35, max(0.0, (max_ratio - 1.0) / 3.0))
    anomaly_pressure = min(0.12, anomaly_count * 0.03)

    maintenance_state = str(maintenance_status.get(zone_id, "online")).lower()
    maintenance_pressure = 0.15 if maintenance_state in {"offline", "maintenance", "failed"} else 0.0

    weather_pressure = 0.0
    if weather is not None:
        wind_speed = float(getattr(weather, "wind_speed_ms", 0.0) or 0.0)
        if wind_speed >= 8.0:
            weather_pressure += 0.05
        if getattr(weather, "wind_direction_deg", 0.0) is not None and 135 <= float(weather.wind_direction_deg) <= 225:
            weather_pressure += 0.03

    shift_pressure = 0.0
    if shifts:
        active_shift_count = sum(1 for shift in shifts if getattr(shift, "zone_id", None) == zone_id)
        if active_shift_count:
            shift_pressure = min(0.08, 0.02 * active_shift_count)

    hazard_class = str(zone_properties.get("hazard_class", "moderate")).lower()
    hazard_multiplier = {"critical": 1.08, "high": 1.05, "moderate": 1.0, "low": 0.95}.get(hazard_class, 1.0)

    raw_score = (
        0.15
        + base_match_score * 0.55
        + permit_pressure * 0.95
        + sensor_pressure * 0.9
        + anomaly_pressure * 0.8
        + maintenance_pressure * 0.9
        + weather_pressure * 0.75
        + shift_pressure * 0.7
    ) * hazard_multiplier

    risk_score = round(_clamp(raw_score, 0.0, 1.0), 3)

    if risk_score >= 0.8:
        risk_level = "critical"
    elif risk_score >= 0.6:
        risk_level = "high"
    elif risk_score >= 0.4:
        risk_level = "medium"
    elif risk_score >= 0.2:
        risk_level = "low"
    else:
        risk_level = "normal"

    drivers = [
        {"name": "hazard_match", "severity": "high" if base_match_score >= 0.6 else "medium", "value": round(base_match_score, 3), "detail": "Causal graph pattern matched against live conditions"},
        {"name": "permit_pressure", "severity": "medium" if permit_pressure >= 0.05 else "low", "value": round(permit_pressure, 3), "detail": "Active permits increase exposure and coordination load"},
        {"name": "sensor_anomaly_pressure", "severity": "high" if max_ratio >= 2.0 else "medium", "value": round(max_ratio, 3), "detail": "Peak sensor deviation from baseline"},
    ]

    if maintenance_pressure:
        drivers.append({"name": "maintenance_condition", "severity": "high", "value": maintenance_state, "detail": "Equipment or ventilation health is degraded"})
    if weather_pressure:
        drivers.append({"name": "weather_drift", "severity": "medium", "value": round(weather_pressure, 3), "detail": "Wind conditions amplify dispersion and exposure risk"})
    if shift_pressure:
        drivers.append({"name": "shift_complexity", "severity": "medium", "value": round(shift_pressure, 3), "detail": "Night-shift or multiple simultaneous crews elevate operational risk"})

    return {
        "zone_id": zone_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_drivers": drivers,
        "active_permit_count": len(active_permits),
        "sensor_anomaly_count": anomaly_count,
        "peak_ratio": round(max_ratio, 3),
    }
