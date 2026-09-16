"""Gemini 1.5 Flash Structured JSON Extractor Fallback.

Core principle:
    AI interprets messy data; deterministic systems establish financial facts.
    Strict structured JSON schema, negative confidence on ambiguity, zero numerical hallucination.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from typing import Optional
from dateutil import parser as date_parser

from src.schemas import EmailMessage, TransactionCandidate


EXTRACTION_PROMPT = """You are a high-precision financial transaction extractor for an enterprise spend intelligence system.
Analyze the following email and extract transactional financial telemetry into structured JSON.

Strict Constraints:
1. ONLY extract monetary values that represent an actual purchase, bill, subscription fee, or refund explicitly stated.
2. If NO numerical amount was charged, paid, refunded, or billed (e.g., mandate registration, confirmation with no amount, corrupted tokens), set "amount": null and "confidence": 0.0.
3. NEVER guess, estimate, or hallucinate numbers not directly written in the email.
4. "merchant": The primary business entity receiving payment or issuing the invoice.
5. "category": Must be one of ["Shopping", "Travel", "Food", "Subscriptions", "Utilities", "Other"].
6. "transaction_type": Must be one of ["purchase", "subscription", "bill", "refund"].
7. "currency": Standard 3-letter ISO currency code (e.g. INR, USD, EUR, GBP).
8. "is_recurring": Boolean flag indicating whether this is an ongoing subscription or recurring bill.
9. "due_date": Date in YYYY-MM-DD format if explicit due date exists for a bill, otherwise null.

Respond ONLY with a valid JSON object matching this schema:
{
  "merchant": "string",
  "amount": float or null,
  "currency": "string",
  "date": "YYYY-MM-DD",
  "category": "string",
  "transaction_type": "string",
  "confidence": float between 0.0 and 1.0,
  "due_date": "YYYY-MM-DD" or null,
  "is_recurring": boolean,
  "reasoning": "string"
}
"""


class GeminiExtractor:
    """Structured extraction fallback supporting both Gemini 1.5 Flash and Groq (Llama-3.3)."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash") -> None:
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
        self.model_name = os.getenv("GEMINI_MODEL", model_name)
        self._client = None
        self.provider = "gemini"

        if self.api_key:
            if self.api_key.startswith("gsk_"):
                self.provider = "groq"
                try:
                    from groq import Groq
                    self._client = Groq(api_key=self.api_key)
                    self.model_name = "llama-3.3-70b-versatile"
                except Exception:
                    self._client = None
            else:
                self.provider = "gemini"
                try:
                    from google import genai
                    self._client = genai.Client(api_key=self.api_key)
                except Exception:
                    self._client = None

    def is_available(self) -> bool:
        """Check if LLM API is configured and accessible."""
        return self._client is not None

    def extract(self, email: EmailMessage) -> Optional[TransactionCandidate]:
        """Call Gemini or Groq to extract structured transaction details."""
        if not self.is_available():
            return None

        email_content = f"""Subject: {email.subject}
Sender: {email.sender}
Date: {email.date_str}
Snippet: {email.snippet}

Body:
{email.body_text}
"""

        try:
            raw_text = None
            if self.provider == "groq":
                chat_completion = self._client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": EXTRACTION_PROMPT},
                        {"role": "user", "content": email_content},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                )
                raw_text = chat_completion.choices[0].message.content
            else:
                from google.genai import types

                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=[EXTRACTION_PROMPT, email_content],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.0,  # Zero temperature for deterministic financial extraction
                    ),
                )
                if response and response.text:
                    raw_text = response.text

            if not raw_text:
                return None

            data = json.loads(raw_text)
            amount = data.get("amount")
            if amount is None or amount <= 0:
                # Anti-hallucination guard: No valid amount extracted
                return None

            # Parse date safely
            raw_date = data.get("date")
            try:
                txn_date = date_parser.parse(raw_date).date() if raw_date else dt.date.today()
            except Exception:
                txn_date = dt.date.today()

            raw_due_date = data.get("due_date")
            due_date = None
            if raw_due_date:
                try:
                    due_date = date_parser.parse(raw_due_date).date()
                except Exception:
                    due_date = None

            category = data.get("category", "Other")
            if category not in ("Shopping", "Travel", "Food", "Subscriptions", "Utilities", "Other"):
                category = "Other"

            txn_type = data.get("transaction_type", "purchase")
            if txn_type not in ("purchase", "subscription", "bill", "refund"):
                txn_type = "purchase"

            confidence = float(data.get("confidence", 0.85))

            return TransactionCandidate(
                merchant=str(data.get("merchant", "Unknown Merchant")).strip(),
                amount=float(amount),
                currency=str(data.get("currency", "INR")).strip().upper(),
                date=txn_date,
                category=category,
                transaction_type=txn_type,
                confidence=confidence,
                source_message_id=email.message_id,
                source_subject=email.subject,
                source_sender=email.sender,
                due_date=due_date,
                is_recurring=bool(data.get("is_recurring", False)),
                raw_extraction_metadata={
                    "extractor": "gemini",
                    "model": self.model_name,
                    "reasoning": data.get("reasoning", ""),
                },
            )
        except Exception:
            return None
