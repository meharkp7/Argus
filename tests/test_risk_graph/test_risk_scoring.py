from types import SimpleNamespace

from backend.risk_graph.geometry import normalize_polygon_geometry
from backend.risk_graph.scoring import score_zone_risk


def test_score_zone_risk_weights_multiple_signals():
    hazard_matches = [
        SimpleNamespace(score=0.92, pattern=SimpleNamespace(severity="critical"), zone_id="ZONE-C")
    ]
    permits = [
        SimpleNamespace(
            zone_id="ZONE-C",
            status=SimpleNamespace(value="active"),
            permit_type=SimpleNamespace(value="hot_work"),
        )
    ]
    sensor_readings = [
        SimpleNamespace(sensor_id="GS-12", zone_id="ZONE-C", gas_type="H2S", value_ppm=250.0, baseline_ppm=100.0)
    ]

    result = score_zone_risk(
        zone_id="ZONE-C",
        hazard_matches=hazard_matches,
        permits=permits,
        sensor_readings=sensor_readings,
        zone_properties={"hazard_class": "critical"},
        maintenance_status={"ZONE-C": "online"},
        shifts=[],
        weather=None,
    )

    assert result["risk_score"] >= 0.75
    assert result["risk_level"] == "critical"
    assert any(driver["name"] == "sensor_anomaly_pressure" for driver in result["risk_drivers"])


def test_normalize_polygon_geometry_closes_ring():
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [[83.2160, 17.6855], [83.2172, 17.6853], [83.2180, 17.6858], [83.2178, 17.6866]]
        ],
    }

    normalized = normalize_polygon_geometry(geometry)

    assert normalized["type"] == "Polygon"
    assert normalized["coordinates"][0][0] == normalized["coordinates"][0][-1]
