"""Emergency response playbooks — deterministic SOAR-style execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.api.schemas import AlertSeverity, CompoundAlert, EmergencyAction


@dataclass
class PlaybookStep:
    step_id: str
    action: str
    channel: str
    requires_approval: bool
    blast_radius: str
    order: int


PLAYBOOKS: dict[str, list[PlaybookStep]] = {
    "gas_ignition": [
        PlaybookStep("EVAC-01", "Initiate zone evacuation protocol", "PA_SYSTEM", False, "zone", 1),
        PlaybookStep("EVAC-02", "Alert emergency response team via SMS/radio", "SMS_RADIO", False, "zone", 2),
        PlaybookStep("GAS-01", "Suspend all hot work permits in affected zone", "PERMIT_SYSTEM", False, "zone", 3),
        PlaybookStep("GAS-02", "Activate supplementary gas monitoring", "SCADA", False, "zone", 4),
        PlaybookStep("EVID-01", "Preserve evidence ledger snapshot", "SYSTEM", False, "plant", 5),
        PlaybookStep("REG-01", "Notify plant safety head and regulatory liaison", "EMAIL", True, "plant", 6),
        PlaybookStep("SHUT-01", "Recommend process isolation (requires human approval)", "SCADA", True, "plant", 7),
    ],
    "h2s_exposure": [
        PlaybookStep("CS-01", "Revoke confined space entry permits", "PERMIT_SYSTEM", False, "zone", 1),
        PlaybookStep("CS-02", "Deploy additional gas monitors at entry points", "IOT", False, "zone", 2),
        PlaybookStep("CS-03", "Verify ventilation system status", "SCADA", False, "zone", 3),
        PlaybookStep("EVAC-03", "Evacuate personnel from affected area", "PA_SYSTEM", False, "zone", 4),
        PlaybookStep("EVID-02", "Preserve evidence ledger snapshot", "SYSTEM", False, "plant", 5),
    ],
    "general_high": [
        PlaybookStep("ALERT-01", "Dispatch alert to safety officer console", "DASHBOARD", False, "zone", 1),
        PlaybookStep("ALERT-02", "Log incident in evidence ledger", "SYSTEM", False, "plant", 2),
        PlaybookStep("ALERT-03", "Notify zone supervisor", "SMS", False, "zone", 3),
    ],
}


class PlaybookEngine:
    """Executes emergency response playbooks with human-approval gates."""

    PATTERN_PLAYBOOK_MAP = {
        "HP-GAS-IGNITION-HOTWORK": "gas_ignition",
        "HP-H2S-EXPOSURE-CONFINED": "h2s_exposure",
    }

    def select_playbook(self, alert: CompoundAlert) -> str:
        return self.PATTERN_PLAYBOOK_MAP.get(
            alert.hazard_pattern_id, "general_high"
        )

    def execute(
        self,
        alert: CompoundAlert,
        operator_confirmed: bool = False,
    ) -> list[EmergencyAction]:
        playbook_id = self.select_playbook(alert)
        steps = PLAYBOOKS.get(playbook_id, PLAYBOOKS["general_high"])

        actions: list[EmergencyAction] = []
        now = datetime.now(timezone.utc)

        for step in sorted(steps, key=lambda s: s.order):
            if step.requires_approval and not operator_confirmed:
                status = "pending_approval"
            else:
                status = "executed"

            actions.append(
                EmergencyAction(
                    step_id=step.step_id,
                    action=step.action,
                    channel=step.channel,
                    status=status,
                    timestamp=now,
                )
            )

        return actions

    def get_playbook_steps(self, playbook_id: str) -> list[dict[str, Any]]:
        steps = PLAYBOOKS.get(playbook_id, [])
        return [
            {
                "step_id": s.step_id,
                "action": s.action,
                "channel": s.channel,
                "requires_approval": s.requires_approval,
                "blast_radius": s.blast_radius,
                "order": s.order,
            }
            for s in steps
        ]
