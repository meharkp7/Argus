"""Weather feed integration with scenario overrides."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.api.schemas import WeatherReading
from backend.config.settings import SCENARIO_PATH, get_settings


class WeatherFeed:
    """Provides weather data from API with scenario-driven overrides."""

    DEFAULT_LOCATION = {"latitude": 17.6870, "longitude": 83.2185}

    def __init__(self, scenario_path=None) -> None:
        self.settings = get_settings()
        path = scenario_path or SCENARIO_PATH
        with open(path, encoding="utf-8") as f:
            self.scenario = json.load(f)

        self._baseline = self.scenario["baseline_conditions"]["weather"]
        self._current = dict(self._baseline)
        self._events = self.scenario["events"]
        self._current_tick = 0

    def reset(self) -> None:
        self._current = dict(self._baseline)
        self._current_tick = 0

    def tick(self) -> WeatherReading:
        for event in self._events:
            if event["tick"] == self._current_tick and event["type"] == "weather_change":
                self._current.update(event["data"])

        self._current_tick += 1

        return WeatherReading(
            timestamp=datetime.now(timezone.utc),
            wind_speed_ms=self._current["wind_speed_ms"],
            wind_direction_deg=self._current["wind_direction_deg"],
            temperature_c=self._current["temperature_c"],
            humidity_pct=self._current["humidity_pct"],
        )

    async def fetch_live(self) -> WeatherReading:
        """Fetch live weather from Open-Meteo API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    self.settings.weather_api_url,
                    params={
                        "latitude": self.DEFAULT_LOCATION["latitude"],
                        "longitude": self.DEFAULT_LOCATION["longitude"],
                        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
                    },
                )
                resp.raise_for_status()
                data = resp.json()["current"]

                return WeatherReading(
                    timestamp=datetime.now(timezone.utc),
                    wind_speed_ms=data["wind_speed_10m"],
                    wind_direction_deg=data["wind_direction_10m"],
                    temperature_c=data["temperature_2m"],
                    humidity_pct=data["relative_humidity_2m"],
                )
        except Exception:
            return self.tick()
