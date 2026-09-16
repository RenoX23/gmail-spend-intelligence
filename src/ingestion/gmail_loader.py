"""Live Gmail batch ingestion loader with query filtering and header parsing."""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import Resource

from src.ingestion.base import BaseIngestionLoader
from src.schemas import EmailMessage


DEFAULT_FINANCIAL_QUERY = (
    "has:attachment OR invoice OR receipt OR payment OR bill OR statement OR order OR subscription"
)


class LiveGmailLoader(BaseIngestionLoader):
    """Fetches candidate financial emails from live user Gmail using minimal scopes."""

    def __init__(
        self,
        service: Resource,
        query: str = DEFAULT_FINANCIAL_QUERY,
        max_results: int = 50,
    ) -> None:
        self.service = service
        self.query = query
        self.max_results = max_results

    def get_source_name(self) -> str:
        return "Live Gmail Inbox (OAuth 2.0 Read-Only)"

    def load_emails(self) -> List[EmailMessage]:
        """Fetch and decode candidate messages from user mailbox."""
        if not self.service:
            raise ValueError("Gmail API service is not initialized or authenticated.")

        # Search messages matching query
        response = (
            self.service.users()
            .messages()
            .list(userId="me", q=self.query, maxResults=self.max_results)
            .execute()
        )

        message_summaries = response.get("messages", [])
        if not message_summaries:
            return []

        loaded_emails: List[EmailMessage] = []

        for msg_summary in message_summaries:
            msg_id = msg_summary["id"]
            try:
                full_msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
                parsed_email = self._parse_gmail_message(full_msg)
                if parsed_email:
                    loaded_emails.append(parsed_email)
            except Exception:
                # Silently skip single corrupted email fetch rather than crashing entire pipeline
                continue

        return loaded_emails

    def _parse_gmail_message(self, raw_msg: Dict[str, Any]) -> Optional[EmailMessage]:
        """Extract headers and plain-text body from Gmail API response."""
        msg_id = raw_msg.get("id", "")
        thread_id = raw_msg.get("threadId")
        snippet = raw_msg.get("snippet", "")
        payload = raw_msg.get("payload", {})
        headers_list = payload.get("headers", [])

        headers_map = {h["name"].lower(): h["value"] for h in headers_list if "name" in h and "value" in h}

        subject = headers_map.get("subject", "(No Subject)")
        sender = headers_map.get("from", "unknown@sender.com")
        recipient = headers_map.get("to")
        date_str = headers_map.get("date", "")

        body_text, body_html = self._extract_body(payload)

        # Fallback to snippet if body decoding is empty
        final_body = body_text.strip() if body_text.strip() else snippet.strip()
        if not final_body:
            final_body = f"Subject: {subject}"

        return EmailMessage(
            message_id=msg_id,
            thread_id=thread_id,
            subject=subject,
            sender=sender,
            recipient=recipient,
            date_str=date_str,
            snippet=snippet,
            body_text=final_body,
            body_html=body_html,
            labels=raw_msg.get("labelIds", []),
        )

    def _extract_body(self, payload: Dict[str, Any]) -> tuple[str, Optional[str]]:
        """Recursively decode text/plain and text/html parts from MIME payload."""
        text_body = ""
        html_body: Optional[str] = None

        mime_type = payload.get("mimeType", "")
        parts = payload.get("parts", [])

        if "body" in payload and "data" in payload["body"]:
            data_bytes = base64.urlsafe_b64decode(payload["body"]["data"])
            decoded_str = data_bytes.decode("utf-8", errors="replace")
            if "text/plain" in mime_type:
                text_body += decoded_str
            elif "text/html" in mime_type:
                html_body = decoded_str

        for part in parts:
            p_text, p_html = self._extract_body(part)
            if p_text:
                text_body += "\n" + p_text
            if p_html and not html_body:
                html_body = p_html

        return text_body.strip(), html_body
