"""Unit tests for deterministic spend metrics and subscription cadence detection."""

from datetime import date
import pytest

from src.analytics.cadence_detector import CadenceDetector
from src.analytics.spend_metrics import SpendMetricsCalculator
from src.extraction.hybrid_engine import HybridExtractionEngine
from src.ingestion.demo_loader import DemoDatasetLoader
from src.schemas import Transaction


@pytest.fixture
def extracted_transactions():
    emails = DemoDatasetLoader().load_emails()
    engine = HybridExtractionEngine()
    result = engine.process_emails(emails)
    return result.transactions


class TestSpendMetrics:
    def test_summary_aggregations(self, extracted_transactions):
        summary = SpendMetricsCalculator.compute_summary(extracted_transactions)

        assert summary.total_spend > 0
        assert summary.total_transactions == len(extracted_transactions)
        assert summary.refunds_total == 1299.00  # Amazon refund
        assert "Shopping" in summary.category_totals
        assert "Food" in summary.category_totals
        assert "Travel" in summary.category_totals
        assert "Subscriptions" in summary.category_totals
        assert "Utilities" in summary.category_totals

        # Verify mathematical consistency: net_spend = gross - refunds
        df = SpendMetricsCalculator.to_dataframe(extracted_transactions)
        gross = df[df["transaction_type"] != "refund"]["amount"].sum()
        assert summary.total_spend == round(gross - 1299.00, 2)

    def test_empty_transactions_state(self):
        """Zero transactions must return clean empty metrics without crashing."""
        summary = SpendMetricsCalculator.compute_summary([])
        assert summary.total_spend == 0.0
        assert summary.total_transactions == 0
        assert summary.active_subscriptions_count == 0
        assert summary.monthly_recurring_total == 0.0
        assert summary.category_totals == {}
        assert summary.merchant_totals == {}

    def test_monthly_trends(self, extracted_transactions):
        trends = SpendMetricsCalculator.compute_monthly_trends(extracted_transactions)
        assert not trends.empty
        assert "month" in trends.columns
        assert "amount" in trends.columns
        # Should span 2026-07, 2026-08, 2026-09
        months = set(trends["month"])
        assert "2026-07" in months or "2026-08" in months or "2026-09" in months

    def test_top_merchants(self, extracted_transactions):
        top = SpendMetricsCalculator.get_top_merchants(extracted_transactions, n=3)
        assert len(top) <= 3
        # Apex Cloud (35,000) or Adobe (multiple months) should be top
        top_names = [m["merchant"] for m in top]
        assert "Apex Cloud Services" in top_names or "Adobe" in top_names


class TestCadenceDetector:
    def test_subscription_detection(self, extracted_transactions):
        subs = CadenceDetector.detect_subscriptions(extracted_transactions)
        merchants = {s.merchant for s in subs}

        assert "Netflix" in merchants
        assert "Spotify" in merchants
        assert "Google One" in merchants
        assert "Adobe" in merchants

        adobe_sub = next(s for s in subs if s.merchant == "Adobe")
        assert adobe_sub.cadence == "monthly"
        assert adobe_sub.observation_count >= 2
