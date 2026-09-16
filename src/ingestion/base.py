"""Abstract base class for email ingestion sources."""

from abc import ABC, abstractmethod
from typing import List

from src.schemas import EmailMessage


class BaseIngestionLoader(ABC):
    """Abstract interface for ingesting emails into the intelligence pipeline."""

    @abstractmethod
    def load_emails(self) -> List[EmailMessage]:
        """Load and return raw email messages."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Return human-readable ingestion mode name."""
        pass
