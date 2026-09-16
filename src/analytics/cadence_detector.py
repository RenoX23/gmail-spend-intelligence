"""Deterministic recurring cadence detector for subscriptions and recurring utility bills."""

from __future__ import annotations

import datetime as dt
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel
import pandas as pd

from src.schemas import Transaction


CadenceType = Literal["monthly", "annual", "irregular", "single_observation"]


class SubscriptionDetail(BaseModel):
    merchant: str
    amount: float
    cadence: CadenceType
    currency: str
    last_billed_date: dt.date
    next_estimated_date: Optional[dt.date] = None
    observation_count: int
    category: str
    source_message_id: str


class CadenceDetector:
    """Detects recurring transaction intervals and projects monthly recurring expenditure."""

    @classmethod
    def detect_subscriptions(cls, transactions: List[Transaction]) -> List[SubscriptionDetail]:
        """Analyze transaction history to identify recurring subscription profiles."""
        if not transactions:
            return []

        # Filter candidates: explicit is_recurring OR subscription transaction_type
        candidates = [t for t in transactions if t.is_recurring or t.transaction_type == "subscription"]
        if not candidates:
            return []

        # Group by merchant
        by_merchant: Dict[str, List[Transaction]] = {}
        for t in candidates:
            by_merchant.setdefault(t.merchant, []).append(t)

        details: List[SubscriptionDetail] = []

        for merchant, txns in by_merchant.items():
            # Sort by date
            sorted_txns = sorted(txns, key=lambda x: x.date)
            latest = sorted_txns[-1]
            count = len(sorted_txns)

            cadence: CadenceType = "monthly"
            next_date: Optional[dt.date] = None

            if count >= 2:
                # Calculate median interval between consecutive charges
                intervals = [
                    (sorted_txns[i].date - sorted_txns[i - 1].date).days
                    for i in range(1, count)
                ]
                avg_interval = sum(intervals) / len(intervals)

                if 25 <= avg_interval <= 35:
                    cadence = "monthly"
                    next_date = latest.date + dt.timedelta(days=30)
                elif 350 <= avg_interval <= 375:
                    cadence = "annual"
                    next_date = latest.date + dt.timedelta(days=365)
                else:
                    cadence = "irregular"
                    next_date = latest.date + dt.timedelta(days=int(avg_interval))
            else:
                # Default monthly for recognized subscription services
                cadence = "monthly"
                next_date = latest.date + dt.timedelta(days=30)

            details.append(
                SubscriptionDetail(
                    merchant=merchant,
                    amount=latest.amount,
                    cadence=cadence,
                    currency=latest.currency,
                    last_billed_date=latest.date,
                    next_estimated_date=next_date,
                    observation_count=count,
                    category=latest.category,
                    source_message_id=latest.source_message_id,
                )
            )

        return sorted(details, key=lambda s: s.amount, reverse=True)
