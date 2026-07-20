"""Central simulation engine coordinating all data streams."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.agents.orchestrator import get_orchestrator
from backend.api.schemas import ShiftRecord, SimulationState
from backend.config.settings import SCENARIO_PATH
from data.simulation.permit_log_generator import PermitLogGenerator
from data.simulation.sensor_stream_generator import SensorStreamGenerator
from data.simulation.weather_feed import WeatherFeed


class SimulationEngine:
    """Orchestrates scenario replay and agent processing."""

    def __init__(self, scenario_path: Path | None = None) -> None:
        path = scenario_path or SCENARIO_PATH
        self.scenario_path = path
        with open(path, encoding="utf-8") as f:
            self.scenario = json.load(f)

        self.sensor_gen = SensorStreamGenerator(path)
        self.permit_gen = PermitLogGenerator(path)
        self.weather_feed = WeatherFeed(path)
        self.orchestrator = get_orchestrator()
        self._running = False
        self._shifts = self._load_shifts()
        self._maintenance = self.scenario["baseline_conditions"]["maintenance_status"]
        self._last_result: dict[str, Any] | None = None

    def _load_shifts(self) -> list[ShiftRecord]:
        roster_path = Path(__file__).parent / "shift_roster.csv"
        shifts = []
        with open(roster_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                shifts.append(
                    ShiftRecord(
                        shift_id=row["shift_id"],
                        zone_id=row["zone_id"],
                        crew_name=row["crew_name"],
                        start_time=datetime.fromisoformat(row["start_time"]),
                        end_time=datetime.fromisoformat(row["end_time"]),
                        overtime_hours=float(row["overtime_hours"]),
                        is_night_shift=row["is_night_shift"].lower() == "true",
                        contractor_ratio=float(row["contractor_ratio"]),
                        experience_level=row["experience_level"],
                    )
                )
        return shifts

    @property
    def state(self) -> SimulationState:
        last_alert = None
        if self._last_result and self._last_result.get("alerts"):
            alerts = self._last_result["alerts"]
            if alerts:
                last_alert = alerts[-1].alert_id if hasattr(alerts[-1], "alert_id") else alerts[-1].get("alert_id")

        return SimulationState(
            running=self._running,
            scenario_id=self.scenario["scenario_id"],
            current_tick=self.sensor_gen.current_tick,
            total_ticks=self.sensor_gen.total_ticks,
            elapsed_seconds=float(self.sensor_gen.current_tick),
            last_alert_id=last_alert,
        )

    def start(self) -> SimulationState:
        self.reset()
        self._running = True
        return self.state

    def stop(self) -> SimulationState:
        self._running = False
        return self.state

    def reset(self) -> None:
        self.sensor_gen.reset()
        self.permit_gen.reset()
        self.weather_feed.reset()
        self._running = False
        self._last_result = None

    def step(self) -> dict[str, Any]:
        """Process one simulation tick through the full pipeline."""
        sensor_readings = self.sensor_gen.tick()
        permits = self.permit_gen.tick()
        weather = self.weather_feed.tick()

        active_shifts = self._get_active_shifts()

        result = self.orchestrator.process_tick(
            sensor_readings=sensor_readings,
            permits=permits,
            shifts=active_shifts,
            weather=weather,
            maintenance_status=self._maintenance,
        )

        result["tick"] = self.sensor_gen.current_tick - 1
        result["weather"] = weather.model_dump(mode="json")
        result["permit_count"] = len(permits)
        result["sensor_count"] = len(sensor_readings)
        self._last_result = result
        return result

    def _get_active_shifts(self) -> list[ShiftRecord]:
        now = datetime.now(timezone.utc)
        return [
            s for s in self._shifts
            if s.start_time.replace(tzinfo=timezone.utc) <= now
            or s.is_night_shift
        ]

    def get_current_readings(self) -> dict[str, Any]:
        if self._last_result:
            return self._last_result
        return self.step()


_engine: SimulationEngine | None = None


def get_simulation_engine() -> SimulationEngine:
    global _engine
    if _engine is None:
        _engine = SimulationEngine()
    return _engine
