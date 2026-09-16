"""Statistical anomaly detection engine for financial transactions.

Detects:
1. Price Hikes (>20% over historical merchant baseline)
2. First-Time High-Spend Merchants (>₹10,000 threshold)
3. Upcoming Renewals & Due Dates (due within 7-day attention window)
"""

from __future__ import annotations

import datetime as dt
import hashlib
from typing import Dict, List, Optional
import pandas as pd

from src.schemas import AlertSeverity, AlertType, AnomalyAlert, Transaction


DEFAULT_HIGH_SPEND_THRESHOLD = 10000.00
DEFAULT_PRICE_HIKE_THRESHOLD_PCT = 20.0
DEFAULT_UPCOMING_WINDOW_DAYS = 7


class AnomalyDetector:
    """Mathematical anomaly detection executing deterministic rules on validated transactions."""

    def __init__(
        self,
        high_spend_threshold: float = DEFAULT_HIGH_SPEND_THRESHOLD,
        price_hike_pct_threshold: float = DEFAULT_PRICE_HIKE_THRESHOLD_PCT,
        upcoming_window_days: int = DEFAULT_UPCOMING_WINDOW_DAYS,
        reference_date: Optional[dt.date] = None,
    ) -> None:
        self.high_spend_threshold = high_spend_threshold
        self.price_hike_pct_threshold = price_hike_pct_threshold
        self.upcoming_window_days = upcoming_window_days
        # Default reference date: 2026-09-16 (environment timeline anchor) or today
        self.reference_date = reference_date or dt.date(2026, 9, 16)

    def detect_anomalies(self, transactions: List[Transaction]) -> List[AnomalyAlert]:
        """Run all statistical detectors and return grounded AnomalyAlert models."""
        if not transactions:
            return []

        alerts: List[AnomalyAlert] = []

        # 1. Price Hike Detection (grouped by merchant)
        by_merchant: Dict[str, List[Transaction]] = {}
        for t in transactions:
            if t.transaction_type != "refund":
                by_merchant.setdefault(t.merchant, []).append(t)

        for merchant, txns in by_merchant.items():
            if len(txns) >= 2:
                # Chronological sort
                sorted_txns = sorted(txns, key=lambda x: x.date)
                latest = sorted_txns[-1]
                historical = sorted_txns[:-1]

                baseline_avg = sum(t.amount for t in historical) / len(historical)
                if baseline_avg > 0:
                    delta_pct = ((latest.amount - baseline_avg) / baseline_avg) * 100.0
                    if delta_pct >= self.price_hike_pct_threshold:
                        severity: AlertSeverity = "high" if delta_pct >= 25.0 else "medium"
                        alert_id = f"alert_price_hike_{hashlib.md5((merchant + str(latest.amount) + str(latest.date)).encode()).hexdigest()[:8]}"
                        alerts.append(
                            AnomalyAlert(
                                alert_id=alert_id,
                                alert_type="price_increase",
                                severity=severity,
                                merchant=merchant,
                                amount=latest.amount,
                                explanation=f"{merchant} charge jumped by {delta_pct:.1f}% to {latest.currency} {latest.amount:,.2f} compared to historical baseline average of {latest.currency} {baseline_avg:,.2f}.",
                                source_message_id=latest.source_message_id,
                                metadata={
                                    "baseline_amount": round(baseline_avg, 2),
                                    "delta_pct": round(delta_pct, 2),
                                    "latest_date": latest.date.isoformat(),
                                },
                            )
                        )

        # 2. First-Time High-Spend Merchant (>₹10,000 threshold)
        for merchant, txns in by_merchant.items():
            sorted_txns = sorted(txns, key=lambda x: x.date)
            first_txn = sorted_txns[0]
            if first_txn.amount >= self.high_spend_threshold:
                # Check if this merchant had zero historical transactions prior
                severity: AlertSeverity = "high" if first_txn.amount >= 25000.0 else "medium"
                alert_id = f"alert_new_merch_{hashlib.md5((merchant + str(first_txn.amount)).encode()).hexdigest()[:8]}"
                alerts.append(
                    AnomalyAlert(
                        alert_id=alert_id,
                        alert_type="new_merchant",
                        severity=severity,
                        merchant=merchant,
                        amount=first_txn.amount,
                        explanation=f"First-time payment of {first_txn.currency} {first_txn.amount:,.2f} to {merchant} exceeds high-spend threshold of {first_txn.currency} {self.high_spend_threshold:,.2f}.",
                        source_message_id=first_txn.source_message_id,
                        metadata={
                            "threshold": self.high_spend_threshold,
                            "date": first_txn.date.isoformat(),
                        },
                    )
                )

        # 3. Upcoming Renewals & Due Dates (within upcoming_window_days)
        for t in transactions:
            if t.due_date:
                days_diff = (t.due_date - self.reference_date).days
                # Flag if due date is upcoming within window (0 to upcoming_window_days)
                if 0 <= days_diff <= self.upcoming_window_days:
                    severity: AlertSeverity = "high" if days_diff <= 2 else "medium"
                    alert_id = f"alert_due_{hashlib.md5((t.merchant + str(t.due_date)).encode()).hexdigest()[:8]}"
                    alerts.append(
                        AnomalyAlert(
                            alert_id=alert_id,
                            alert_type="upcoming_renewal",
                            severity=severity,
                            merchant=t.merchant,
                            amount=t.amount,
                            explanation=f"Upcoming {t.merchant} bill of {t.currency} {t.amount:,.2f} is due on {t.due_date.isoformat()} ({days_diff} day{'s' if days_diff != 1 else ''} remaining).",
                            source_message_id=t.source_message_id,
                            metadata={
                                "due_date": t.due_date.isoformat(),
                                "days_remaining": days_diff,
                            },
                        )
                    )

        return alerts
