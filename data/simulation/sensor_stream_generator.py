"""Physics-informed sensor stream generator for demo scenarios."""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.api.schemas import SensorReading
from backend.config.settings import SCENARIO_PATH


class SensorStreamGenerator:
    """Generates realistic sensor readings from scenario definitions."""

    def __init__(self, scenario_path: Path | None = None) -> None:
        path = scenario_path or SCENARIO_PATH
        with open(path, encoding="utf-8") as f:
            self.scenario = json.load(f)

        self.baselines = self.scenario["sensor_baselines"]
        self.events = sorted(self.scenario["events"], key=lambda e: e["tick"])
        self._active_drifts: dict[str, dict[str, Any]] = {}
        self._current_tick = 0
        self._start_time = datetime.now(timezone.utc)

    @property
    def total_ticks(self) -> int:
        return self.scenario["duration_minutes"] * 60

    @property
    def current_tick(self) -> int:
        return self._current_tick

    def reset(self) -> None:
        self._current_tick = 0
        self._active_drifts = {}
        self._start_time = datetime.now(timezone.utc)

    def tick(self) -> list[SensorReading]:
        self._process_events()
        readings = self._generate_readings()
        self._current_tick += 1
        return readings

    def _process_events(self) -> None:
        for event in self.events:
            if event["tick"] == self._current_tick:
                if event["type"] == "sensor_drift_start":
                    self._active_drifts[event["data"]["sensor_id"]] = {
                        **event["data"],
                        "start_tick": self._current_tick,
                    }

    def _generate_readings(self) -> list[SensorReading]:
        readings = []
        timestamp = self._start_time + timedelta(seconds=self._current_tick)

        for sensor_id, baseline in self.baselines.items():
            value = baseline["baseline_ppm"]
            noise = self._gaussian_noise(baseline["baseline_ppm"] * 0.02)

            if sensor_id in self._active_drifts:
                drift = self._active_drifts[sensor_id]
                elapsed = self._current_tick - drift["start_tick"]
                progress = min(1.0, elapsed / drift["duration_ticks"])

                if drift["drift_profile"] == "exponential":
                    multiplier = 1.0 + (drift["target_multiplier"] - 1.0) * (
                        1 - math.exp(-3 * progress)
                    )
                else:
                    multiplier = 1.0 + (drift["target_multiplier"] - 1.0) * progress

                value = baseline["baseline_ppm"] * multiplier

            value += noise
            value = max(0, value)

            readings.append(
                SensorReading(
                    sensor_id=sensor_id,
                    zone_id=baseline["zone_id"],
                    timestamp=timestamp,
                    gas_type=baseline["gas_type"],
                    value_ppm=round(value, 2),
                    baseline_ppm=baseline["baseline_ppm"],
                    latitude=baseline.get("latitude"),
                    longitude=baseline.get("longitude"),
                )
            )

        return readings

    def _gaussian_noise(self, std: float) -> float:
        import random
        return random.gauss(0, std)

    def get_events_at_tick(self, tick: int) -> list[dict[str, Any]]:
        return [e for e in self.events if e["tick"] == tick]
