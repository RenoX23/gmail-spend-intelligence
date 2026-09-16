"""Unit tests for statistical anomaly detection and AI explanation layer."""

from datetime import date
from unittest.mock import MagicMock
import pytest

from src.anomaly.detector import AnomalyDetector
from src.anomaly.explainer import AnomalyExplainer
from src.extraction.hybrid_engine import HybridExtractionEngine
from src.ingestion.demo_loader import DemoDatasetLoader
from src.schemas import AnomalyAlert, Transaction


@pytest.fixture
def extracted_transactions():
    emails = DemoDatasetLoader().load_emails()
    engine = HybridExtractionEngine()
    result = engine.process_emails(emails)
    return result.transactions


class TestAnomalyDetector:
    def test_price_hike_detected(self, extracted_transactions):
        detector = AnomalyDetector(reference_date=date(2026, 9, 16))
        alerts = detector.detect_anomalies(extracted_transactions)

        price_hike_alerts = [a for a in alerts if a.alert_type == "price_increase"]
        assert len(price_hike_alerts) >= 1

        adobe_alert = next((a for a in price_hike_alerts if a.merchant == "Adobe"), None)
        assert adobe_alert is not None
        assert adobe_alert.amount == 6899.00
        assert adobe_alert.metadata["baseline_amount"] == 5499.00
        assert adobe_alert.metadata["delta_pct"] >= 25.0
        assert adobe_alert.severity == "high"

    def test_new_high_spend_merchant_detected(self, extracted_transactions):
        detector = AnomalyDetector(reference_date=date(2026, 9, 16))
        alerts = detector.detect_anomalies(extracted_transactions)

        new_merch_alerts = [a for a in alerts if a.alert_type == "new_merchant"]
        assert len(new_merch_alerts) >= 1

        apex_alert = next((a for a in new_merch_alerts if "Apex" in a.merchant), None)
        assert apex_alert is not None
        assert apex_alert.amount == 35000.00
        assert apex_alert.severity == "high"

    def test_upcoming_renewals_detected(self, extracted_transactions):
        detector = AnomalyDetector(reference_date=date(2026, 9, 16), upcoming_window_days=7)
        alerts = detector.detect_anomalies(extracted_transactions)

        renewal_alerts = [a for a in alerts if a.alert_type == "upcoming_renewal"]
        assert len(renewal_alerts) >= 2

        merchants = {a.merchant for a in renewal_alerts}
        assert "Airtel" in merchants
        assert "BESCOM" in merchants

    def test_empty_transactions_state(self):
        detector = AnomalyDetector()
        alerts = detector.detect_anomalies([])
        assert alerts == []


class TestAnomalyExplainer:
    def test_deterministic_fallback(self):
        explainer = AnomalyExplainer(api_key=None)
        assert not explainer.is_available()

        alert = AnomalyAlert(
            alert_id="a1",
            alert_type="price_increase",
            severity="high",
            merchant="Adobe",
            amount=6899.00,
            explanation="Adobe charge increased by 25.5%",
            source_message_id="msg_adobe",
        )
        exp = explainer.explain(alert)
        assert exp == "Adobe charge increased by 25.5%"

    def test_gemini_mocked_explanation(self):
        explainer = AnomalyExplainer(api_key="fake_key")
        mock_response = MagicMock()
        mock_response.text = "Your Adobe subscription jumped 25.5% to Rs 6,899. We recommend reviewing your active plan."
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        explainer._client = mock_client

        alert = AnomalyAlert(
            alert_id="a1",
            alert_type="price_increase",
            severity="high",
            merchant="Adobe",
            amount=6899.00,
            explanation="Base explanation",
            source_message_id="msg_adobe",
        )
        exp = explainer.explain(alert)
        assert "Adobe subscription jumped 25.5%" in exp

    def test_groq_mocked_explanation(self):
        from src.anomaly.explainer import AnomalyExplainer
        explainer = AnomalyExplainer(api_key="gsk_fake_key_999")
        assert explainer.provider == "groq"

        mock_choice = MagicMock()
        mock_choice.message.content = "Groq analysis: Adobe subscription cost increased significantly over historical baseline."
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion
        explainer._client = mock_client

        alert = AnomalyAlert(
            alert_id="a1",
            alert_type="price_increase",
            severity="high",
            merchant="Adobe",
            amount=6899.00,
            explanation="Base explanation",
            source_message_id="msg_adobe",
        )
        exp = explainer.explain(alert)
        assert "Groq analysis" in exp
