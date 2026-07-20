"""Hard regulatory constraints for permit validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from backend.api.schemas import PermitRecord, PermitType


@dataclass
class RuleViolation:
    rule_id: str
    framework: str
    clause: str
    description: str
    severity: str


class PermitRuleEngine:
    """Enforces hard regulatory constraints on permits."""

    RULES = {
        "OISD-GDN-117-01": {
            "framework": "OISD",
            "clause": "OISD-GDN-117 Section 4.2",
            "description": "Hot work prohibited within 15m of active gas monitoring alarm",
            "permit_types": [PermitType.HOT_WORK],
            "severity": "critical",
        },
        "OISD-GDN-117-02": {
            "framework": "OISD",
            "clause": "OISD-GDN-117 Section 5.1",
            "description": "Hot work requires gas-free certificate for confined adjacent areas",
            "permit_types": [PermitType.HOT_WORK],
            "severity": "high",
        },
        "OISD-GDN-126-01": {
            "framework": "OISD",
            "clause": "OISD-GDN-126 Section 3.3",
            "description": "Confined space entry requires continuous gas monitoring",
            "permit_types": [PermitType.CONFINED_SPACE],
            "severity": "critical",
        },
        "DGMS-CIRC-01": {
            "framework": "DGMS",
            "clause": "DGMS Circular on simultaneous operations",
            "description": "Simultaneous hot work and lifting prohibited in same zone",
            "permit_types": [PermitType.HOT_WORK, PermitType.LIFTING],
            "severity": "critical",
        },
        "FACTORY-ACT-41B": {
            "framework": "Factory Act",
            "clause": "Section 41B",
            "description": "Hazardous process requires approved safety report compliance",
            "permit_types": [PermitType.HOT_WORK, PermitType.CONFINED_SPACE],
            "severity": "high",
        },
        "FACTORY-ACT-22": {
            "framework": "Factory Act",
            "clause": "Section 22",
            "description": "Lifting operations require certified rigger and spotter",
            "permit_types": [PermitType.LIFTING],
            "severity": "medium",
        },
    }

    GAS_ALARM_ZONES = {"ZONE-C", "ZONE-D"}
    MAX_PERMIT_DURATION = timedelta(hours=12)
    MIN_PERMIT_NOTICE = timedelta(hours=1)

    def evaluate(
        self,
        permit: PermitRecord,
        active_permits: list[PermitRecord],
        sensor_anomaly_zones: list[str] | None = None,
    ) -> list[RuleViolation]:
        violations: list[RuleViolation] = []
        sensor_anomaly_zones = sensor_anomaly_zones or []

        if (
            permit.permit_type == PermitType.HOT_WORK
            and permit.zone_id in self.GAS_ALARM_ZONES
            and permit.zone_id in sensor_anomaly_zones
        ):
            violations.append(
                RuleViolation(
                    rule_id="OISD-GDN-117-01",
                    framework="OISD",
                    clause="OISD-GDN-117 Section 4.2",
                    description=(
                        f"Hot work in {permit.zone_id} prohibited: active gas monitoring "
                        f"alarm in zone"
                    ),
                    severity="critical",
                )
            )

        duration = permit.end_time - permit.start_time
        if duration > self.MAX_PERMIT_DURATION:
            violations.append(
                RuleViolation(
                    rule_id="OISD-DURATION-01",
                    framework="OISD",
                    clause="OISD-GDN-117 Section 2.1",
                    description=f"Permit duration {duration} exceeds maximum 12 hours",
                    severity="high",
                )
            )

        for active in active_permits:
            if active.permit_id == permit.permit_id:
                continue
            if active.zone_id != permit.zone_id:
                continue

            if (
                permit.permit_type == PermitType.HOT_WORK
                and active.permit_type == PermitType.LIFTING
            ) or (
                permit.permit_type == PermitType.LIFTING
                and active.permit_type == PermitType.HOT_WORK
            ):
                violations.append(
                    RuleViolation(
                        rule_id="DGMS-CIRC-01",
                        framework="DGMS",
                        clause="DGMS Circular on simultaneous operations",
                        description=(
                            f"SIMOPS violation: {permit.permit_type.value} cannot overlap "
                            f"with {active.permit_type.value} in {permit.zone_id}"
                        ),
                        severity="critical",
                    )
                )

            if (
                permit.permit_type == PermitType.HOT_WORK
                and active.permit_type == PermitType.CONFINED_SPACE
            ):
                violations.append(
                    RuleViolation(
                        rule_id="OISD-GDN-117-02",
                        framework="OISD",
                        clause="OISD-GDN-117 Section 5.1",
                        description=(
                            "Hot work with concurrent confined space entry requires "
                            "gas-free certificate verification"
                        ),
                        severity="high",
                    )
                )

        if permit.permit_type == PermitType.CONFINED_SPACE:
            if permit.zone_id in sensor_anomaly_zones:
                violations.append(
                    RuleViolation(
                        rule_id="OISD-GDN-126-01",
                        framework="OISD",
                        clause="OISD-GDN-126 Section 3.3",
                        description=(
                            "Confined space entry prohibited with active gas anomaly "
                            "in zone"
                        ),
                        severity="critical",
                    )
                )

        return violations
