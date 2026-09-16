"""Unit tests for regex extractors, deduplication, and the hybrid extraction engine."""

from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from src.extraction.deduplicator import TransactionDeduplicator
from src.extraction.hybrid_engine import HybridExtractionEngine
from src.extraction.regex_extractors import RegexVendorExtractor
from src.ingestion.demo_loader import DemoDatasetLoader
from src.schemas import EmailMessage, Transaction


@pytest.fixture
def demo_emails():
    return DemoDatasetLoader().load_emails()


class TestRegexExtractors:
    def test_amazon_purchase_extraction(self, demo_emails):
        amazon_email = next(e for e in demo_emails if e.message_id == "msg_amazon_2026_0901")
        candidate = RegexVendorExtractor.extract(amazon_email)
        assert candidate is not None
        assert candidate.merchant == "Amazon"
        assert candidate.amount == 2499.00
        assert candidate.category == "Shopping"
        assert candidate.confidence >= 0.85

    def test_swiggy_extraction(self, demo_emails):
        swiggy_email = next(e for e in demo_emails if e.message_id == "msg_swiggy_2026_0903")
        candidate = RegexVendorExtractor.extract(swiggy_email)
        assert candidate is not None
        assert candidate.merchant == "Swiggy"
        assert candidate.amount == 620.00
        assert candidate.category == "Food"

    def test_uber_extraction(self, demo_emails):
        uber_email = next(e for e in demo_emails if e.message_id == "msg_uber_2026_0905")
        candidate = RegexVendorExtractor.extract(uber_email)
        assert candidate is not None
        assert candidate.merchant == "Uber"
        assert candidate.amount == 435.50
        assert candidate.category == "Travel"

    def test_netflix_recurring_extraction(self, demo_emails):
        netflix_email = next(e for e in demo_emails if e.message_id == "msg_netflix_2026_0908")
        candidate = RegexVendorExtractor.extract(netflix_email)
        assert candidate is not None
        assert candidate.merchant == "Netflix"
        assert candidate.amount == 649.00
        assert candidate.is_recurring is True
        assert candidate.category == "Subscriptions"

    def test_amazon_refund_extraction(self, demo_emails):
        refund_email = next(e for e in demo_emails if e.message_id == "msg_amazon_refund_2026_0911")
        candidate = RegexVendorExtractor.extract(refund_email)
        assert candidate is not None
        assert candidate.merchant == "Amazon"
        assert candidate.amount == 1299.00
        assert candidate.transaction_type == "refund"

    def test_airtel_bill_with_due_date(self, demo_emails):
        airtel_email = next(e for e in demo_emails if e.message_id == "msg_airtel_fiber_2026_0913")
        candidate = RegexVendorExtractor.extract(airtel_email)
        assert candidate is not None
        assert candidate.merchant == "Airtel"
        assert candidate.amount == 1179.00
        assert candidate.due_date is not None
        assert candidate.due_date == date(2026, 9, 18)


class TestDeduplicator:
    def test_order_id_deduplication(self):
        txn1 = Transaction(
            transaction_id="txn_1",
            merchant="Amazon",
            amount=999.00,
            currency="INR",
            date=date(2026, 9, 9),
            category="Shopping",
            transaction_type="purchase",
            confidence=0.98,
            source_message_id="msg_orig",
            source_subject="Ordered: Mouse (Order #402-9981245-1122334)",
            source_sender="auto-confirm@amazon.in",
        )
        txn2 = Transaction(
            transaction_id="txn_2",
            merchant="Amazon",
            amount=999.00,
            currency="INR",
            date=date(2026, 9, 9),
            category="Shopping",
            transaction_type="purchase",
            confidence=0.98,
            source_message_id="msg_dup",
            source_subject="Duplicate Invoice: Mouse (Order #402-9981245-1122334)",
            source_sender="auto-confirm@amazon.in",
        )

        res = TransactionDeduplicator.deduplicate([txn1, txn2])
        assert len(res.unique_transactions) == 1
        assert len(res.duplicate_records) == 1
        assert res.unique_transactions[0].source_message_id == "msg_orig"
        assert res.duplicate_records[0]["rejected_message_id"] == "msg_dup"


class TestHybridEngineEndToEnd:
    def test_pipeline_on_synthetic_dataset(self, demo_emails):
        engine = HybridExtractionEngine()
        result = engine.process_emails(demo_emails)

        # Verified transactions must exist
        assert len(result.transactions) >= 12

        # Filtered noise must include campus, newsletter, linkedin
        noise_ids = {e.message_id for e in result.filtered_out_noise}
        assert "msg_noise_college_2026_0904" in noise_ids
        assert "msg_noise_newsletter_2026_0906" in noise_ids
        assert "msg_noise_linkedin_2026_0908" in noise_ids

        # Missing amounts (HDFC auto debit) and corrupt text must be rejected
        rejected_ids = {r["message_id"] for r in result.rejected_extractions}
        assert "msg_hdfc_no_amount_2026_0902" in rejected_ids

        # Duplicate Amazon receipt must be caught
        dup_rejected_ids = {d["rejected_message_id"] for d in result.duplicates_detected}
        assert "msg_amazon_dup_copy_2026_0909_b" in dup_rejected_ids

        # Ensure all resulting transactions have confidence >= 0.85
        assert all(t.confidence >= 0.85 for t in result.transactions)
        assert all(t.amount > 0 for t in result.transactions)


class TestGeminiExtractor:
    def test_unconfigured_gemini_returns_none(self):
        from src.extraction.gemini_extractor import GeminiExtractor
        extractor = GeminiExtractor(api_key=None)
        assert not extractor.is_available()
        email = EmailMessage(
            message_id="test_msg",
            subject="Invoice",
            sender="billing@saas.com",
            date_str="2026-09-01",
            body_text="Invoice amount: $50",
        )
        assert extractor.extract(email) is None

    def test_gemini_mocked_success(self):
        from src.extraction.gemini_extractor import GeminiExtractor
        extractor = GeminiExtractor(api_key="fake_key")
        mock_response = MagicMock()
        mock_response.text = '{"merchant": "Acme Cloud", "amount": 149.00, "currency": "USD", "date": "2026-09-10", "category": "Utilities", "transaction_type": "bill", "confidence": 0.95, "is_recurring": true, "reasoning": "Monthly compute"}'

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        extractor._client = mock_client

        email = EmailMessage(
            message_id="msg_acme",
            subject="Your Acme Cloud Statement",
            sender="billing@acme.com",
            date_str="2026-09-10",
            body_text="Your balance of $149.00 was charged.",
        )
        candidate = extractor.extract(email)
        assert candidate is not None
        assert candidate.merchant == "Acme Cloud"
        assert candidate.amount == 149.00
        assert candidate.currency == "USD"
        assert candidate.is_recurring is True

    def test_gemini_anti_hallucination_guard(self):
        """When Gemini returns null amount, extractor must reject."""
        from src.extraction.gemini_extractor import GeminiExtractor
        extractor = GeminiExtractor(api_key="fake_key")
        mock_response = MagicMock()
        mock_response.text = '{"merchant": "Unknown", "amount": null, "currency": "INR", "confidence": 0.0, "reasoning": "No monetary amount"}'

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        extractor._client = mock_client

        email = EmailMessage(
            message_id="msg_null",
            subject="Notice",
            sender="info@bank.com",
            date_str="2026-09-10",
            body_text="Your mandate is registered.",
        )
        assert extractor.extract(email) is None

