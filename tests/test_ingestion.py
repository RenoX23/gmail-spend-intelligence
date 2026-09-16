"""Unit tests for ingestion loaders and OAuth handler."""

from unittest.mock import MagicMock
import pytest

from src.auth.gmail_oauth import GMAIL_SCOPES, GmailOAuthHandler
from src.ingestion.demo_loader import DemoDatasetLoader
from src.ingestion.gmail_loader import LiveGmailLoader


class TestDemoDatasetLoader:
    def test_demo_loader_reads_dataset(self):
        loader = DemoDatasetLoader()
        assert "Synthetic Demo" in loader.get_source_name()
        emails = loader.load_emails()
        assert len(emails) >= 18
        assert all(e.message_id for e in emails)


class TestGmailOAuthSecurity:
    def test_scope_is_strictly_read_only(self):
        """Security invariant: Only gmail.readonly is requested."""
        assert GMAIL_SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]

    def test_oauth_unconfigured_graceful(self, tmp_path):
        fake_secrets = tmp_path / "non_existent_creds.json"
        fake_token = tmp_path / "non_existent_token.json"
        handler = GmailOAuthHandler(client_secrets_file=fake_secrets, token_path=fake_token)
        assert not handler.is_configured()
        assert handler.get_credentials(allow_browser_flow=False) is None
        assert handler.get_gmail_service() is None


class TestLiveGmailLoader:
    def test_requires_service(self):
        with pytest.raises(ValueError, match="not initialized"):
            loader = LiveGmailLoader(service=None)
            loader.load_emails()

    def test_mock_fetch_and_parse(self):
        mock_service = MagicMock()
        mock_messages = mock_service.users().messages()
        mock_messages.list().execute.return_value = {
            "messages": [{"id": "live_msg_001"}]
        }
        mock_messages.get().execute.return_value = {
            "id": "live_msg_001",
            "threadId": "th_001",
            "snippet": "Payment receipt for INR 500",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Your Order Receipt"},
                    {"name": "From", "value": "billing@vendor.com"},
                    {"name": "Date", "value": "Mon, 1 Sep 2026 10:00:00 +0000"},
                ],
                "mimeType": "text/plain",
                "body": {"data": "UGF5bWVudCByZWNlaXB0IGZvciBJTlIgNTAw"},  # Base64 for "Payment receipt for INR 500"
            },
            "labelIds": ["INBOX"],
        }

        loader = LiveGmailLoader(service=mock_service)
        results = loader.load_emails()
        assert len(results) == 1
        assert results[0].message_id == "live_msg_001"
        assert results[0].subject == "Your Order Receipt"
        assert results[0].sender == "billing@vendor.com"
