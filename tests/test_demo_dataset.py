"""Test validation for synthetic demo dataset completeness and integrity."""

import json
from pathlib import Path
import pytest
from src.schemas import EmailMessage


DEMO_DATA_PATH = Path(__file__).parent.parent / "demo_data" / "synthetic_emails.json"


class TestDemoDataset:
    @pytest.fixture
    def dataset(self):
        assert DEMO_DATA_PATH.exists(), f"File {DEMO_DATA_PATH} not found"
        with open(DEMO_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

    def test_minimum_case_count(self, dataset):
        """Must have at least 18 test cases per TASK.md specification."""
        assert len(dataset) >= 18, f"Expected at least 18 cases, got {len(dataset)}"

    def test_all_cases_parse_as_email_messages(self, dataset):
        """All items must deserialize into valid EmailMessage schema."""
        for item in dataset:
            email = EmailMessage(
                message_id=item["message_id"],
                thread_id=item.get("thread_id"),
                subject=item["subject"],
                sender=item["sender"],
                recipient=item.get("recipient"),
                date_str=item["date_str"],
                snippet=item.get("snippet", ""),
                body_text=item["body_text"],
            )
            assert email.message_id
            assert email.subject
            assert email.sender
            assert email.body_text

    def test_contains_all_mandated_edge_cases(self, dataset):
        scenario_ids = {case["scenario_id"] for case in dataset}

        # 1. Normal purchases
        assert any("amazon_normal" in s for s in scenario_ids)
        assert any("swiggy" in s for s in scenario_ids)
        assert any("uber" in s for s in scenario_ids)

        # 2. Subscriptions
        assert any("netflix" in s for s in scenario_ids)
        assert any("spotify" in s for s in scenario_ids)

        # 3. Price hikes
        assert any("adobe_price_hike" in s for s in scenario_ids)

        # 4. Large anomalous new merchant
        assert any("apex_cloud" in s for s in scenario_ids)

        # 5. Missing amounts
        assert any("missing_amount" in s for s in scenario_ids)

        # 6. Duplicate emails
        assert any("dup_original" in s for s in scenario_ids)
        assert any("dup_resend" in s for s in scenario_ids)

        # 7. Refunds
        assert any("refund" in s for s in scenario_ids)

        # 8. Upcoming renewals / utility due dates
        assert any("upcoming_renewal" in s or "electricity" in s for s in scenario_ids)

        # 9. Non-financial noise
        assert any("noise" in s for s in scenario_ids)
