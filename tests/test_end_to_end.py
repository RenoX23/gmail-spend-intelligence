"""End-to-end integration tests verifying the full Polarisk pipeline."""

from datetime import date
import pytest

from src.analytics.cadence_detector import CadenceDetector
from src.analytics.spend_metrics import SpendMetricsCalculator
from src.anomaly.detector import AnomalyDetector
from src.extraction.hybrid_engine import HybridExtractionEngine
from src.ingestion.demo_loader import DemoDatasetLoader


class TestEndToEndPipeline:
    def test_complete_pipeline_flow(self):
        # 1. Ingest synthetic demo suite
        loader = DemoDatasetLoader()
        raw_emails = loader.load_emails()
        assert len(raw_emails) >= 18

        # 2. Execute Hybrid Extraction Engine
        engine = HybridExtractionEngine()
        pipeline_result = engine.process_emails(raw_emails)

        # 3. Assert schema validation and deduplication
        txns = pipeline_result.transactions
        assert len(txns) >= 12
        assert all(t.confidence >= 0.85 for t in txns)
        assert all(t.amount > 0 for t in txns)

        # 4. Assert noise filtration
        noise_ids = [e.message_id for e in pipeline_result.filtered_out_noise]
        assert "msg_noise_college_2026_0904" in noise_ids
        assert "msg_noise_newsletter_2026_0906" in noise_ids
        assert "msg_noise_linkedin_2026_0908" in noise_ids

        # 5. Assert duplicate suppression
        dup_ids = [d["rejected_message_id"] for d in pipeline_result.duplicates_detected]
        assert "msg_amazon_dup_copy_2026_0909_b" in dup_ids

        # 6. Assert deterministic financial metrics
        summary = SpendMetricsCalculator.compute_summary(txns)
        assert summary.total_spend > 0
        assert summary.refunds_total == 1299.00
        assert summary.active_subscriptions_count >= 3

        # 7. Assert cadence detection
        subscriptions = CadenceDetector.detect_subscriptions(txns)
        sub_merchants = {s.merchant for s in subscriptions}
        assert {"Netflix", "Spotify", "Google One", "Adobe"}.issubset(sub_merchants)

        # 8. Assert statistical anomaly alerts
        detector = AnomalyDetector(reference_date=date(2026, 9, 16))
        alerts = detector.detect_anomalies(txns)
        alert_types = {a.alert_type for a in alerts}
        assert "price_increase" in alert_types
        assert "new_merchant" in alert_types
        assert "upcoming_renewal" in alert_types

        # 9. Assert 100% email provenance traceability
        email_map = {e.message_id: e for e in raw_emails}
        for txn in txns:
            assert txn.source_message_id in email_map
            assert email_map[txn.source_message_id].subject == txn.source_subject

        for alert in alerts:
            assert alert.source_message_id in email_map
