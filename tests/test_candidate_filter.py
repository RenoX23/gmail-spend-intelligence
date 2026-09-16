"""Unit tests for the deterministic Candidate Relevance Filter."""

import json
from pathlib import Path
import pytest

from src.ingestion.candidate_filter import CandidateFilter
from src.schemas import EmailMessage


DEMO_DATA_PATH = Path(__file__).parent.parent / "demo_data" / "synthetic_emails.json"


@pytest.fixture
def demo_emails():
    with open(DEMO_DATA_PATH, "r", encoding="utf-8") as f:
        raw_cases = json.load(f)
    return [
        (
            case["scenario_id"],
            case["is_financial"],
            EmailMessage(
                message_id=case["message_id"],
                subject=case["subject"],
                sender=case["sender"],
                date_str=case["date_str"],
                snippet=case.get("snippet", ""),
                body_text=case["body_text"],
            ),
        )
        for case in raw_cases
    ]


class TestCandidateFilter:
    def test_filter_accuracy_on_synthetic_suite(self, demo_emails):
        """Verify that every synthetic test case matches its ground truth classification."""
        for scenario_id, expected_is_financial, email in demo_emails:
            result = CandidateFilter.evaluate(email)
            assert (
                result.is_financial == expected_is_financial
            ), f"Scenario '{scenario_id}' failed: expected is_financial={expected_is_financial}, got {result.is_financial}. Reason: {result.rejection_reason}"

    def test_noise_filtration(self):
        college_noise = EmailMessage(
            message_id="msg_noise_1",
            subject="Campus recruitment registration portal open for graduates",
            sender="placement@university.edu",
            date_str="2026-09-01",
            body_text="Please register on the Dean of Placement portal.",
        )
        result = CandidateFilter.evaluate(college_noise)
        assert not result.is_financial
        assert "Matched non-financial noise" in result.rejection_reason

    def test_batch_partitioning(self, demo_emails):
        emails = [email for _, _, email in demo_emails]
        candidates, discarded = CandidateFilter.filter_batch(emails)
        assert len(candidates) > 0
        assert len(discarded) > 0
        assert len(candidates) + len(discarded) == len(emails)
