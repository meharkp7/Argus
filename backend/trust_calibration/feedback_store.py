"""Feedback capture and active-learning threshold adjustment."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.api.schemas import AlertFeedback, FeedbackLabel, TrustCalibrationMetrics
from backend.config.settings import FEEDBACK_DB_PATH, get_settings


class FeedbackStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or FEEDBACK_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    operator_id TEXT NOT NULL,
                    comment TEXT,
                    timestamp TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threshold_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    compound_risk_threshold REAL NOT NULL,
                    sensor_zscore_threshold REAL NOT NULL,
                    false_positive_rate REAL NOT NULL,
                    feedback_count INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_outcomes (
                    alert_id TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    had_feedback INTEGER DEFAULT 0
                )
                """
            )
            conn.commit()

    def record_alert(
        self,
        alert_id: str,
        severity: str,
        confidence: float,
        timestamp: datetime | None = None,
    ) -> None:
        ts = (timestamp or datetime.now(timezone.utc)).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO alert_outcomes
                (alert_id, severity, confidence, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (alert_id, severity, confidence, ts),
            )
            conn.commit()

    def submit_feedback(self, feedback: AlertFeedback) -> AlertFeedback:
        ts = feedback.timestamp or datetime.now(timezone.utc)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO alert_feedback
                (alert_id, label, operator_id, comment, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    feedback.alert_id,
                    feedback.label.value,
                    feedback.operator_id,
                    feedback.comment,
                    ts.isoformat(),
                ),
            )
            conn.execute(
                "UPDATE alert_outcomes SET had_feedback = 1 WHERE alert_id = ?",
                (feedback.alert_id,),
            )
            conn.commit()

        feedback.timestamp = ts
        return feedback

    def get_all_feedback(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM alert_feedback ORDER BY timestamp ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def compute_metrics(self) -> TrustCalibrationMetrics:
        with self._connect() as conn:
            total_alerts = conn.execute(
                "SELECT COUNT(*) FROM alert_outcomes"
            ).fetchone()[0]
            feedback_rows = conn.execute(
                "SELECT * FROM alert_feedback ORDER BY timestamp ASC"
            ).fetchall()
            history_rows = conn.execute(
                "SELECT * FROM threshold_history ORDER BY timestamp ASC"
            ).fetchall()

        feedback_count = len(feedback_rows)
        false_alarms = sum(
            1 for r in feedback_rows if r["label"] == FeedbackLabel.FALSE_ALARM.value
        )
        useful = sum(
            1 for r in feedback_rows if r["label"] == FeedbackLabel.USEFUL.value
        )

        fp_rate = false_alarms / feedback_count if feedback_count > 0 else 0.0
        precision = useful / feedback_count if feedback_count > 0 else 1.0

        fp_history = []
        cumulative_fp = 0
        cumulative_total = 0
        for i, row in enumerate(feedback_rows):
            cumulative_total += 1
            if row["label"] == FeedbackLabel.FALSE_ALARM.value:
                cumulative_fp += 1
            fp_history.append(
                {
                    "feedback_number": i + 1,
                    "false_positive_rate": cumulative_fp / cumulative_total,
                    "timestamp": row["timestamp"],
                }
            )

        settings = get_settings()
        return TrustCalibrationMetrics(
            total_alerts=total_alerts,
            feedback_count=feedback_count,
            false_positive_rate=round(fp_rate, 4),
            precision=round(precision, 4),
            threshold_adjustments=[dict(r) for r in history_rows],
            history=fp_history,
        )


class ThresholdUpdater:
    """Active-learning threshold adjustment based on operator feedback."""

    MIN_THRESHOLD = 0.50
    MAX_THRESHOLD = 0.95
    ADJUSTMENT_STEP = 0.02

    def __init__(self, store: FeedbackStore | None = None) -> None:
        self.store = store or FeedbackStore()
        self.settings = get_settings()

    def update_thresholds(self) -> dict[str, float]:
        metrics = self.store.compute_metrics()

        compound_threshold = self.settings.compound_risk_threshold
        sensor_threshold = self.settings.sensor_zscore_threshold

        if metrics.feedback_count >= 3:
            if metrics.false_positive_rate > 0.3:
                compound_threshold = min(
                    self.MAX_THRESHOLD,
                    compound_threshold + self.ADJUSTMENT_STEP,
                )
                sensor_threshold = min(4.0, sensor_threshold + 0.1)
            elif metrics.false_positive_rate < 0.1 and metrics.precision > 0.8:
                compound_threshold = max(
                    self.MIN_THRESHOLD,
                    compound_threshold - self.ADJUSTMENT_STEP,
                )

        self._record_adjustment(
            compound_threshold, sensor_threshold, metrics
        )

        return {
            "compound_risk_threshold": compound_threshold,
            "sensor_zscore_threshold": sensor_threshold,
        }

    def _record_adjustment(
        self,
        compound: float,
        sensor: float,
        metrics: TrustCalibrationMetrics,
    ) -> None:
        with self.store._connect() as conn:
            conn.execute(
                """
                INSERT INTO threshold_history
                (timestamp, compound_risk_threshold, sensor_zscore_threshold,
                 false_positive_rate, feedback_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    compound,
                    sensor,
                    metrics.false_positive_rate,
                    metrics.feedback_count,
                ),
            )
            conn.commit()

    def get_current_thresholds(self) -> dict[str, float]:
        with self.store._connect() as conn:
            row = conn.execute(
                "SELECT * FROM threshold_history ORDER BY id DESC LIMIT 1"
            ).fetchone()

        if row:
            return {
                "compound_risk_threshold": row["compound_risk_threshold"],
                "sensor_zscore_threshold": row["sensor_zscore_threshold"],
            }

        return {
            "compound_risk_threshold": self.settings.compound_risk_threshold,
            "sensor_zscore_threshold": self.settings.sensor_zscore_threshold,
        }


_feedback_store: FeedbackStore | None = None
_threshold_updater: ThresholdUpdater | None = None


def get_feedback_store() -> FeedbackStore:
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store


def get_threshold_updater() -> ThresholdUpdater:
    global _threshold_updater
    if _threshold_updater is None:
        _threshold_updater = ThresholdUpdater(get_feedback_store())
    return _threshold_updater
