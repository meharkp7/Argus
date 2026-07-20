"""Industrial causal risk graph model loaded from schema."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config.settings import RISK_GRAPH_SCHEMA_PATH


@dataclass
class ConditionNode:
    id: str
    label: str
    category: str
    evaluation: str
    description: str
    threshold: float | None = None
    permit_types: list[str] = field(default_factory=list)
    window_minutes: int | None = None


@dataclass
class HazardPattern:
    id: str
    name: str
    severity: str
    description: str
    required_conditions: list[dict[str, Any]]
    amplifying_conditions: list[dict[str, Any]]
    historical_precedents: list[str]
    recommended_actions: list[str]
    regulatory_references: list[str]


@dataclass
class CausalRiskGraph:
    version: str
    hazard_patterns: list[HazardPattern]
    condition_nodes: dict[str, ConditionNode]
    zone_adjacency: dict[str, list[str]]
    sensor_zone_mapping: dict[str, str]

    @classmethod
    def from_schema(cls, schema_path: Path | None = None) -> CausalRiskGraph:
        path = schema_path or RISK_GRAPH_SCHEMA_PATH
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        condition_nodes = {}
        for node_data in data["condition_nodes"]:
            node = ConditionNode(
                id=node_data["id"],
                label=node_data["label"],
                category=node_data["category"],
                evaluation=node_data["evaluation"],
                description=node_data["description"],
                threshold=node_data.get("threshold"),
                permit_types=node_data.get("permit_types", []),
                window_minutes=node_data.get("window_minutes"),
            )
            condition_nodes[node.id] = node

        hazard_patterns = [
            HazardPattern(
                id=hp["id"],
                name=hp["name"],
                severity=hp["severity"],
                description=hp["description"],
                required_conditions=hp["required_conditions"],
                amplifying_conditions=hp.get("amplifying_conditions", []),
                historical_precedents=hp.get("historical_precedents", []),
                recommended_actions=hp.get("recommended_actions", []),
                regulatory_references=hp.get("regulatory_references", []),
            )
            for hp in data["hazard_patterns"]
        ]

        return cls(
            version=data.get("version", "1.0.0"),
            hazard_patterns=hazard_patterns,
            condition_nodes=condition_nodes,
            zone_adjacency=data.get("zone_adjacency", {}),
            sensor_zone_mapping=data.get("sensor_zone_mapping", {}),
        )

    def get_hazard_pattern(self, pattern_id: str) -> HazardPattern | None:
        for hp in self.hazard_patterns:
            if hp.id == pattern_id:
                return hp
        return None

    def get_condition(self, node_id: str) -> ConditionNode | None:
        return self.condition_nodes.get(node_id)

    def get_zone_for_sensor(self, sensor_id: str) -> str | None:
        return self.sensor_zone_mapping.get(sensor_id)

    def get_adjacent_zones(self, zone_id: str) -> list[str]:
        return self.zone_adjacency.get(zone_id, [])


_graph_instance: CausalRiskGraph | None = None


def get_risk_graph() -> CausalRiskGraph:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = CausalRiskGraph.from_schema()
    return _graph_instance
