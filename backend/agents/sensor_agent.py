"""Per-sensor anomaly detection using rolling z-score, EWMA, and isolation forest."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from backend.api.schemas import SensorReading
from backend.config.settings import get_settings


@dataclass
class SensorAnomaly:
    sensor_id: str
    zone_id: str
    gas_type: str
    timestamp: datetime
    value_ppm: float
    baseline_ppm: float
    z_score: float
    ewma_value: float
    ratio_to_baseline: float
    isolation_score: float
    is_anomalous: bool
    severity: str
    details: dict[str, Any] = field(default_factory=dict)


class SensorAgent:
    """Detects anomalies in individual sensor streams."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._history: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=self.settings.sensor_baseline_window)
        )
        self._ewma: dict[str, float] = {}
        self._multivariate_buffer: dict[str, deque[list[float]]] = defaultdict(
            lambda: deque(maxlen=50)
        )

    def analyze(self, readings: list[SensorReading]) -> list[SensorAnomaly]:
        anomalies: list[SensorAnomaly] = []

        for reading in readings:
            anomaly = self._analyze_single(reading)
            if anomaly.is_anomalous:
                anomalies.append(anomaly)

        zone_readings: dict[str, list[SensorReading]] = defaultdict(list)
        for reading in readings:
            zone_readings[reading.zone_id].append(reading)

        for zone_id, zone_sensors in zone_readings.items():
            multivariate_anomalies = self._multivariate_check(zone_id, zone_sensors)
            existing_ids = {a.sensor_id for a in anomalies}
            for ma in multivariate_anomalies:
                if ma.sensor_id not in existing_ids:
                    anomalies.append(ma)

        return anomalies

    def _analyze_single(self, reading: SensorReading) -> SensorAnomaly:
        sensor_id = reading.sensor_id
        history = self._history[sensor_id]
        history.append(reading.value_ppm)

        alpha = self.settings.sensor_ewma_alpha
        if sensor_id in self._ewma:
            self._ewma[sensor_id] = (
                alpha * reading.value_ppm + (1 - alpha) * self._ewma[sensor_id]
            )
        else:
            self._ewma[sensor_id] = reading.value_ppm

        ewma_val = self._ewma[sensor_id]

        if len(history) >= 5:
            values = np.array(history)
            mean = float(np.mean(values))
            std = float(np.std(values))
            z_score = (reading.value_ppm - mean) / std if std > 0 else 0.0
        else:
            z_score = 0.0

        ratio = (
            reading.value_ppm / reading.baseline_ppm
            if reading.baseline_ppm > 0
            else 1.0
        )

        zscore_anomalous = abs(z_score) >= self.settings.sensor_zscore_threshold
        ratio_anomalous = ratio >= 2.0
        is_anomalous = zscore_anomalous or ratio_anomalous

        if ratio >= 3.0 or abs(z_score) >= 4.0:
            severity = "critical"
        elif ratio >= 2.0 or abs(z_score) >= self.settings.sensor_zscore_threshold:
            severity = "high"
        elif ratio >= 1.5:
            severity = "medium"
        else:
            severity = "normal"

        return SensorAnomaly(
            sensor_id=sensor_id,
            zone_id=reading.zone_id,
            gas_type=reading.gas_type,
            timestamp=reading.timestamp,
            value_ppm=reading.value_ppm,
            baseline_ppm=reading.baseline_ppm,
            z_score=round(z_score, 3),
            ewma_value=round(ewma_val, 3),
            ratio_to_baseline=round(ratio, 3),
            isolation_score=0.0,
            is_anomalous=is_anomalous,
            severity=severity,
            details={
                "zscore_anomalous": zscore_anomalous,
                "ratio_anomalous": ratio_anomalous,
                "history_length": len(history),
            },
        )

    def _multivariate_check(
        self,
        zone_id: str,
        readings: list[SensorReading],
    ) -> list[SensorAnomaly]:
        if len(readings) < 2:
            return []

        features = []
        for r in readings:
            ratio = r.value_ppm / r.baseline_ppm if r.baseline_ppm > 0 else 1.0
            features.append([r.value_ppm, ratio])

        buffer = self._multivariate_buffer[zone_id]
        buffer.append(features[0])

        if len(buffer) < 10:
            return []

        X = np.array(list(buffer))
        mean = np.mean(X[:-1], axis=0)
        std = np.std(X[:-1], axis=0)
        std = np.where(std < 1e-6, 1.0, std)
        z_scores = np.abs((X[-1] - mean) / std)
        latest_score = float(np.max(z_scores))
        is_outlier = latest_score >= self.settings.sensor_zscore_threshold

        anomalies = []
        if is_outlier:
            reading = readings[0]
            ratio = reading.value_ppm / reading.baseline_ppm if reading.baseline_ppm > 0 else 1.0
            anomalies.append(
                SensorAnomaly(
                    sensor_id=reading.sensor_id,
                    zone_id=zone_id,
                    gas_type=reading.gas_type,
                    timestamp=reading.timestamp,
                    value_ppm=reading.value_ppm,
                    baseline_ppm=reading.baseline_ppm,
                    z_score=0.0,
                    ewma_value=reading.value_ppm,
                    ratio_to_baseline=round(ratio, 3),
                    isolation_score=round(latest_score, 3),
                    is_anomalous=True,
                    severity="high",
                    details={"detection_method": "rolling_multivariate_zscore"},
                )
            )

        return anomalies

    def baseline_would_trigger(self, readings: list[SensorReading]) -> bool:
        """Naive single-threshold baseline: any sensor > 3x baseline."""
        for reading in readings:
            if reading.baseline_ppm > 0:
                if reading.value_ppm / reading.baseline_ppm >= 3.0:
                    return True
        return False
