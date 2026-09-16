"""Deterministic spend metrics calculations using Pandas.

Core principle:
    Deterministic systems establish financial facts.
    LLMs never compute aggregates; all totals, category distributions,
    and merchant rankings are computed with mathematical precision in Pandas.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd

from src.schemas import CategoryType, SpendSummary, Transaction


class SpendMetricsCalculator:
    """Computes deterministic financial aggregations from validated transactions."""

    @classmethod
    def to_dataframe(cls, transactions: List[Transaction]) -> pd.DataFrame:
        """Convert list of Pydantic Transaction models to pandas DataFrame."""
        if not transactions:
            return pd.DataFrame(columns=[
                "transaction_id", "merchant", "amount", "currency", "date",
                "category", "transaction_type", "confidence", "source_message_id",
                "source_subject", "source_sender", "due_date", "is_recurring"
            ])

        records = [t.model_dump() for t in transactions]
        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        if "due_date" in df.columns:
            df["due_date"] = pd.to_datetime(df["due_date"])
        return df

    @classmethod
    def compute_summary(cls, transactions: List[Transaction]) -> SpendSummary:
        """Generate high-level deterministic spend summary."""
        if not transactions:
            return SpendSummary(
                total_spend=0.0,
                total_transactions=0,
                active_subscriptions_count=0,
                monthly_recurring_total=0.0,
                category_totals={},
                merchant_totals={},
                refunds_total=0.0,
                alerts_count=0,
            )

        df = cls.to_dataframe(transactions)

        # Net Spend calculation: purchases + subscriptions + bills - refunds
        purchases_df = df[df["transaction_type"] != "refund"]
        refunds_df = df[df["transaction_type"] == "refund"]

        gross_spend = float(purchases_df["amount"].sum()) if not purchases_df.empty else 0.0
        total_refunds = float(refunds_df["amount"].sum()) if not refunds_df.empty else 0.0
        net_spend = max(0.0, gross_spend - total_refunds)

        # Recurring Subscriptions
        sub_df = df[df["is_recurring"] == True]
        active_sub_count = int(sub_df["merchant"].nunique()) if not sub_df.empty else 0
        monthly_recurring_total = float(sub_df["amount"].sum()) if not sub_df.empty else 0.0

        # Category Breakdown
        category_totals: Dict[CategoryType, float] = {}
        if not purchases_df.empty:
            cat_series = purchases_df.groupby("category")["amount"].sum()
            category_totals = {cat: float(val) for cat, val in cat_series.items()}

        # Merchant Totals
        merchant_totals: Dict[str, float] = {}
        if not purchases_df.empty:
            merch_series = purchases_df.groupby("merchant")["amount"].sum().sort_values(ascending=False)
            merchant_totals = {str(merch): float(val) for merch, val in merch_series.items()}

        return SpendSummary(
            total_spend=round(net_spend, 2),
            total_transactions=len(transactions),
            active_subscriptions_count=active_sub_count,
            monthly_recurring_total=round(monthly_recurring_total, 2),
            category_totals=category_totals,
            merchant_totals=merchant_totals,
            refunds_total=round(total_refunds, 2),
            alerts_count=0,
        )

    @classmethod
    def compute_monthly_trends(cls, transactions: List[Transaction]) -> pd.DataFrame:
        """Aggregate spend by YYYY-MM period."""
        if not transactions:
            return pd.DataFrame(columns=["month", "amount", "transaction_count"])

        df = cls.to_dataframe(transactions)
        spend_df = df[df["transaction_type"] != "refund"].copy()
        if spend_df.empty:
            return pd.DataFrame(columns=["month", "amount", "transaction_count"])

        spend_df["month"] = spend_df["date"].dt.to_period("M").astype(str)
        grouped = spend_df.groupby("month").agg(
            amount=("amount", "sum"),
            transaction_count=("transaction_id", "count")
        ).reset_index()
        grouped["amount"] = grouped["amount"].round(2)
        return grouped.sort_values("month")

    @classmethod
    def get_top_merchants(cls, transactions: List[Transaction], n: int = 5) -> List[Dict[str, Any]]:
        """Return top N merchants by total spend."""
        if not transactions:
            return []
        df = cls.to_dataframe(transactions)
        spend_df = df[df["transaction_type"] != "refund"]
        if spend_df.empty:
            return []
        top = spend_df.groupby("merchant")["amount"].sum().sort_values(ascending=False).head(n)
        return [{"merchant": str(k), "amount": round(float(v), 2)} for k, v in top.items()]
