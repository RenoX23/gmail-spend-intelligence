"""Pydantic v2 data contracts for Polarisk Gmail Spend Intelligence.

Core principle:
    Deterministic systems establish financial facts.
    Strict schema validation, positive amount gates, confidence scoring,
    and categorical literals.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


CategoryType = Literal[
    "Shopping",
    "Travel",
    "Food",
    "Subscriptions",
    "Utilities",
    "Other",
]

TransactionType = Literal[
    "purchase",
    "subscription",
    "bill",
    "refund",
]

AlertSeverity = Literal[
    "low",
    "medium",
    "high",
]

AlertType = Literal[
    "price_increase",
    "new_merchant",
    "upcoming_renewal",
    "unusual_amount",
]


class EmailMessage(BaseModel):
    """Raw ingested email representation."""

    message_id: str = Field(..., description="Unique Gmail message ID or synthetic ID")
    thread_id: Optional[str] = Field(default=None, description="Gmail thread ID if available")
    subject: str = Field(..., description="Subject header of the email")
    sender: str = Field(..., description="From header (email address or display name)")
    recipient: Optional[str] = Field(default=None, description="To header")
    date_str: str = Field(..., description="Raw date string from email headers or ISO string")
    snippet: str = Field(default="", description="Short snippet of the email body")
    body_text: str = Field(..., description="Plain-text decoded body of the email")
    body_html: Optional[str] = Field(default=None, description="Raw HTML body if available")
    labels: List[str] = Field(default_factory=list, description="Gmail labels attached to the email")

    @field_validator("message_id", "subject", "sender", "body_text")
    @classmethod
    def reject_empty_strings(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class TransactionCandidate(BaseModel):
    """Intermediate extracted candidate before confidence gating & deduplication."""

    merchant: str = Field(..., description="Extracted vendor or merchant name")
    amount: Optional[float] = Field(default=None, description="Extracted transaction amount")
    currency: str = Field(default="INR", description="Three-letter ISO currency code")
    date: Optional[dt.date] = Field(default=None, description="Transaction date")
    category: CategoryType = Field(default="Other", description="Spending category")
    transaction_type: TransactionType = Field(default="purchase", description="Type of transaction")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Extraction confidence score")
    source_message_id: str = Field(..., description="Foreign key to originating EmailMessage")
    source_subject: str = Field(..., description="Original subject line")
    source_sender: str = Field(..., description="Original sender")
    due_date: Optional[dt.date] = Field(default=None, description="Payment due date if bill/invoice")
    is_recurring: bool = Field(default=False, description="Whether this is a recurring charge")
    raw_extraction_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadata from parser (e.g. regex pattern, LLM model)"
    )


class Transaction(BaseModel):
    """Validated, production-grade financial transaction entity."""

    transaction_id: str = Field(..., description="Unique deterministic transaction hash/UUID")
    merchant: str = Field(..., description="Normalized merchant name")
    amount: float = Field(gt=0, description="Transaction amount in specified currency (strictly > 0)")
    currency: str = Field(default="INR", description="Standardized currency ISO code")
    date: dt.date = Field(..., description="ISO 8601 transaction date")
    category: CategoryType = Field(..., description="Validated financial category")
    transaction_type: TransactionType = Field(default="purchase", description="purchase, subscription, bill, refund")
    confidence: float = Field(ge=0.85, le=1.0, description="Strict confidence gate: minimum 0.85 for analytics")
    source_message_id: str = Field(..., description="Email traceability: originating message ID")
    source_subject: str = Field(..., description="Email traceability: originating subject line")
    source_sender: str = Field(..., description="Email traceability: originating sender header")
    due_date: Optional[dt.date] = Field(default=None, description="Upcoming due date for bills/renewals")
    is_recurring: bool = Field(default=False, description="Flag indicating recurring subscription charge")

    @field_validator("merchant")
    @classmethod
    def clean_merchant(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Merchant name cannot be blank")
        return clean

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        code = v.strip().upper()
        # Common symbol normalizations
        if code in ("₹", "RS", "RS.", "INR"):
            return "INR"
        if code in ("$", "USD"):
            return "USD"
        if code in ("€", "EUR"):
            return "EUR"
        if code in ("£", "GBP"):
            return "GBP"
        return code

    @model_validator(mode="after")
    def validate_confidence_and_amount(self) -> "Transaction":
        if self.amount <= 0:
            raise ValueError(f"Amount must be strictly positive, got {self.amount}")
        if self.confidence < 0.85:
            raise ValueError(
                f"Confidence {self.confidence} fails production threshold (min 0.85 required)"
            )
        return self


class AnomalyAlert(BaseModel):
    """Grounded anomaly alert model with full email provenance."""

    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: AlertType = Field(
        ...,
        description="Type: price_increase, new_merchant, upcoming_renewal, unusual_amount",
    )
    severity: AlertSeverity = Field(default="medium", description="Alert severity level")
    merchant: str = Field(..., description="Affected merchant name")
    amount: float = Field(..., description="Transaction or renewal amount")
    explanation: str = Field(..., description="Grounded, evidence-backed natural language explanation")
    source_message_id: str = Field(..., description="Email traceability: originating message ID")
    detected_at: dt.datetime = Field(default_factory=dt.datetime.utcnow, description="Detection timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Statistical evidence (e.g. baseline, delta_pct, due_date)"
    )


class SpendSummary(BaseModel):
    """Deterministic spend aggregation summary."""

    total_spend: float = Field(ge=0.0, description="Total net spend in default currency")
    total_transactions: int = Field(ge=0, description="Count of valid transactions")
    active_subscriptions_count: int = Field(ge=0, description="Count of active recurring subscriptions")
    monthly_recurring_total: float = Field(ge=0.0, description="Monthly recurring run rate")
    category_totals: Dict[CategoryType, float] = Field(
        default_factory=dict, description="Spend totals by category"
    )
    merchant_totals: Dict[str, float] = Field(
        default_factory=dict, description="Spend totals by merchant"
    )
    refunds_total: float = Field(default=0.0, ge=0.0, description="Total refunded amount")
    alerts_count: int = Field(default=0, ge=0, description="Number of active anomalies detected")
