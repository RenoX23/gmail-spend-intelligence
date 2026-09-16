"""Unit tests for Pydantic v2 data models and validation constraints."""

from datetime import date
import pytest
from pydantic import ValidationError

from src.schemas import (
    AnomalyAlert,
    EmailMessage,
    SpendSummary,
    Transaction,
    TransactionCandidate,
)


class TestEmailMessageSchema:
    def test_valid_email_message(self):
        msg = EmailMessage(
            message_id="msg_123",
            subject="Your Amazon Order Receipt",
            sender="orders@amazon.in",
            date_str="2026-09-01T10:00:00+05:30",
            snippet="Order placed successfully for INR 2,499.00",
            body_text="Full invoice text with INR 2,499.00 details",
        )
        assert msg.message_id == "msg_123"
        assert msg.subject == "Your Amazon Order Receipt"
        assert msg.labels == []

    def test_empty_string_rejection(self):
        with pytest.raises(ValidationError):
            EmailMessage(
                message_id="   ",
                subject="Subject",
                sender="orders@amazon.in",
                date_str="2026-09-01",
                body_text="Some text",
            )


class TestTransactionSchema:
    def test_valid_transaction(self):
        txn = Transaction(
            transaction_id="txn_001",
            merchant="Amazon",
            amount=2499.00,
            currency="INR",
            date=date(2026, 9, 1),
            category="Shopping",
            transaction_type="purchase",
            confidence=0.98,
            source_message_id="msg_123",
            source_subject="Order #402-1829103",
            source_sender="auto-confirm@amazon.in",
        )
        assert txn.amount == 2499.00
        assert txn.confidence >= 0.85
        assert txn.currency == "INR"

    def test_reject_zero_or_negative_amount(self):
        with pytest.raises(ValidationError):
            Transaction(
                transaction_id="txn_zero",
                merchant="Amazon",
                amount=0.0,
                currency="INR",
                date=date(2026, 9, 1),
                category="Shopping",
                transaction_type="purchase",
                confidence=0.95,
                source_message_id="msg_123",
                source_subject="Receipt",
                source_sender="auto-confirm@amazon.in",
            )

        with pytest.raises(ValidationError):
            Transaction(
                transaction_id="txn_neg",
                merchant="Amazon",
                amount=-50.0,
                currency="INR",
                date=date(2026, 9, 1),
                category="Shopping",
                transaction_type="purchase",
                confidence=0.95,
                source_message_id="msg_123",
                source_subject="Receipt",
                source_sender="auto-confirm@amazon.in",
            )

    def test_confidence_threshold_gate(self):
        """Confidence score must be strictly >= 0.85."""
        with pytest.raises(ValidationError):
            Transaction(
                transaction_id="txn_low_conf",
                merchant="Uber",
                amount=435.50,
                currency="INR",
                date=date(2026, 9, 5),
                category="Travel",
                transaction_type="purchase",
                confidence=0.75,  # Below 0.85 threshold!
                source_message_id="msg_456",
                source_subject="Uber Ride",
                source_sender="uber@uber.com",
            )

    def test_currency_normalization(self):
        for raw, expected in [("₹", "INR"), ("Rs", "INR"), ("rs.", "INR"), ("$", "USD"), ("inr", "INR")]:
            txn = Transaction(
                transaction_id=f"txn_{raw}",
                merchant="Swiggy",
                amount=620.00,
                currency=raw,
                date=date(2026, 9, 3),
                category="Food",
                transaction_type="purchase",
                confidence=0.95,
                source_message_id="msg_789",
                source_subject="Swiggy Order",
                source_sender="orders@swiggy.in",
            )
            assert txn.currency == expected

    def test_category_literal_enforcement(self):
        with pytest.raises(ValidationError):
            Transaction(
                transaction_id="txn_bad_cat",
                merchant="Netflix",
                amount=649.00,
                currency="INR",
                date=date(2026, 9, 8),
                category="Entertainment",  # Must be 'Subscriptions' or valid CategoryType
                transaction_type="subscription",
                confidence=0.99,
                source_message_id="msg_999",
                source_subject="Netflix Renewal",
                source_sender="info@mailer.netflix.com",
            )


class TestAnomalyAlertSchema:
    def test_valid_anomaly_alert(self):
        alert = AnomalyAlert(
            alert_id="alert_001",
            alert_type="price_increase",
            severity="high",
            merchant="Adobe",
            amount=6899.00,
            explanation="Monthly subscription charge increased by 25.46% (₹5,499.00 -> ₹6,899.00).",
            source_message_id="msg_adobe_spike",
            metadata={"baseline": 5499.00, "delta_pct": 25.46},
        )
        assert alert.alert_type == "price_increase"
        assert alert.severity == "high"
        assert alert.amount == 6899.00
        assert alert.metadata["delta_pct"] == 25.46


class TestSpendSummarySchema:
    def test_valid_spend_summary(self):
        summary = SpendSummary(
            total_spend=12345.50,
            total_transactions=15,
            active_subscriptions_count=4,
            monthly_recurring_total=1898.00,
            category_totals={"Shopping": 4398.0, "Food": 620.0},
            merchant_totals={"Amazon": 3498.0, "Swiggy": 620.0},
            refunds_total=1299.00,
            alerts_count=3,
        )
        assert summary.total_spend == 12345.50
        assert summary.alerts_count == 3
