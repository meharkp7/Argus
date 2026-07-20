"""Geometry normalization helpers for robust map rendering."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def normalize_polygon_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    """Ensure polygon rings are closed and coordinates are normalized."""

    if not geometry or geometry.get("type") != "Polygon":
        return geometry

    normalized = deepcopy(geometry)
    coordinates = normalized.get("coordinates", [])
    if not coordinates:
        return normalized

    normalized_coords: list[list[list[float]]] = []
    for ring in coordinates:
        if not ring:
            continue
        ring_copy = [list(point) for point in ring]
        first = ring_copy[0]
        last = ring_copy[-1]
        if first != last:
            ring_copy.append(first)
        normalized_coords.append(ring_copy)

    normalized["coordinates"] = normalized_coords
    return normalized
