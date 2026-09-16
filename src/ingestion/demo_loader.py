"""Synthetic demo dataset loader for zero-credential offline evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from src.ingestion.base import BaseIngestionLoader
from src.schemas import EmailMessage


DEFAULT_DEMO_PATH = Path(__file__).parent.parent.parent / "demo_data" / "synthetic_emails.json"


class DemoDatasetLoader(BaseIngestionLoader):
    """Loads bundled synthetic emails demonstrating 18+ rich financial edge cases."""

    def __init__(self, file_path: Optional[Path | str] = None) -> None:
        self.file_path = Path(file_path) if file_path else DEFAULT_DEMO_PATH
        if not self.file_path.exists():
            raise FileNotFoundError(f"Synthetic demo dataset not found at {self.file_path}")

    def get_source_name(self) -> str:
        return "Synthetic Demo Dataset (Offline Mode)"

    def load_emails(self) -> List[EmailMessage]:
        """Parse demo dataset JSON into EmailMessage instances."""
        with open(self.file_path, "r", encoding="utf-8") as f:
            raw_cases = json.load(f)

        emails: List[EmailMessage] = []
        for case in raw_cases:
            email = EmailMessage(
                message_id=case["message_id"],
                thread_id=case.get("thread_id"),
                subject=case["subject"],
                sender=case["sender"],
                recipient=case.get("recipient"),
                date_str=case["date_str"],
                snippet=case.get("snippet", ""),
                body_text=case["body_text"],
                labels=["DEMO_DATASET"],
            )
            emails.append(email)

        return emails
