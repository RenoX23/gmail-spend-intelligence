"""High-speed deterministic regex extractors for standard financial email templates.

Sub-millisecond latency parsing for Amazon, Swiggy, Uber, Flipkart, Netflix,
Spotify, Google One, Adobe, Airtel, BESCOM, and standard receipt structures.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Optional
from dateutil import parser as date_parser

from src.schemas import CategoryType, EmailMessage, TransactionCandidate, TransactionType


def _parse_amount(raw_str: str) -> Optional[float]:
    """Clean string currency tokens into float."""
    cleaned = re.sub(r"[^\d.]", "", raw_str)
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def _parse_date_safe(raw_str: str, default_date: dt.date) -> dt.date:
    """Safely parse various human and ISO date formats."""
    try:
        # fuzzy=True allows extracting date from lines like 'Date: 03 Sep 2026, 07:42 PM'
        parsed = date_parser.parse(raw_str, fuzzy=True)
        return parsed.date()
    except Exception:
        return default_date


class RegexVendorExtractor:
    """Deterministic regex pattern matcher for high-frequency merchants."""

    @classmethod
    def extract(cls, email: EmailMessage) -> Optional[TransactionCandidate]:
        """Attempt to extract transaction using vendor-specific and generalized regex."""
        sender = (email.sender or "").lower()
        subject = email.subject or ""
        body = email.body_text or ""
        combined = f"{subject}\n{body}"

        # Default fallback date from email date header
        fallback_date = _parse_date_safe(email.date_str, dt.date.today())

        # 1. Amazon India Refund
        if "amazon" in sender and ("refund" in subject.lower() or "refund" in body.lower()):
            m_amount = re.search(r"(?:refund\s+(?:amount|of)[\s:]*(?:rs\.?|inr|₹)\s*)([\d,]+(?:\.\d{2})?)", combined, re.IGNORECASE)
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    return TransactionCandidate(
                        merchant="Amazon",
                        amount=amt,
                        currency="INR",
                        date=fallback_date,
                        category="Shopping",
                        transaction_type="refund",
                        confidence=0.97,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=False,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "amazon_refund"},
                    )

        # 2. Amazon India Purchases
        if "amazon" in sender or "amazon.in" in combined.lower():
            # Grand Total or Total: Rs. 2,499.00
            m_amount = re.search(
                r"(?:grand\s+total|total\s+payable|total\s+amount|order\s+total|total)[\s:]*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)",
                combined,
                re.IGNORECASE,
            )
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    # Extract date from 'Order Date: ...'
                    m_date = re.search(r"(?:order\s+date|date)[\s:]*([^\n\r]+)", body, re.IGNORECASE)
                    txn_date = _parse_date_safe(m_date.group(1), fallback_date) if m_date else fallback_date
                    return TransactionCandidate(
                        merchant="Amazon",
                        amount=amt,
                        currency="INR",
                        date=txn_date,
                        category="Shopping",
                        transaction_type="purchase",
                        confidence=0.98,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=False,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "amazon"},
                    )

        # 3. Swiggy
        if "swiggy" in sender or "swiggy" in combined.lower():
            m_amount = re.search(
                r"(?:total\s+paid|order\s+total)[\s:]*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)",
                combined,
                re.IGNORECASE,
            )
            if not m_amount:
                m_amount = re.search(
                    r"(?<!item\s)(?<!sub)total[\s:]*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)",
                    combined,
                    re.IGNORECASE,
                )
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    m_date = re.search(r"date[\s:]*([^\n\r]+)", body, re.IGNORECASE)
                    txn_date = _parse_date_safe(m_date.group(1), fallback_date) if m_date else fallback_date
                    return TransactionCandidate(
                        merchant="Swiggy",
                        amount=amt,
                        currency="INR",
                        date=txn_date,
                        category="Food",
                        transaction_type="purchase",
                        confidence=0.96,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=False,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "swiggy"},
                    )

        # 4. Uber
        if "uber" in sender or "uber" in combined.lower():
            m_amount = re.search(
                r"(?:total\s+fare|total|uber\s*-\s*inr)[\s:]*(?:inr|rs\.?|₹)?\s*([\d,]+(?:\.\d{2})?)",
                combined,
                re.IGNORECASE,
            )
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    m_date = re.search(r"date[\s:]*([^\n\r]+)", body, re.IGNORECASE)
                    txn_date = _parse_date_safe(m_date.group(1), fallback_date) if m_date else fallback_date
                    return TransactionCandidate(
                        merchant="Uber",
                        amount=amt,
                        currency="INR",
                        date=txn_date,
                        category="Travel",
                        transaction_type="purchase",
                        confidence=0.97,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=False,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "uber"},
                    )

        # 5. Flipkart
        if "flipkart" in sender or "flipkart" in combined.lower():
            m_amount = re.search(
                r"(?:total\s+amount\s+payable|total)[\s:]*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)",
                combined,
                re.IGNORECASE,
            )
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    m_date = re.search(r"order\s+date[\s:]*([^\n\r]+)", body, re.IGNORECASE)
                    txn_date = _parse_date_safe(m_date.group(1), fallback_date) if m_date else fallback_date
                    return TransactionCandidate(
                        merchant="Flipkart",
                        amount=amt,
                        currency="INR",
                        date=txn_date,
                        category="Shopping",
                        transaction_type="purchase",
                        confidence=0.95,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=False,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "flipkart"},
                    )

        # 6. Netflix
        if "netflix" in sender or "netflix" in combined.lower():
            m_amount = re.search(r"(?:amount|fee\s+of)[\s:]*(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{2})?)", combined, re.IGNORECASE)
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    return TransactionCandidate(
                        merchant="Netflix",
                        amount=amt,
                        currency="INR",
                        date=fallback_date,
                        category="Subscriptions",
                        transaction_type="subscription",
                        confidence=0.99,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=True,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "netflix"},
                    )

        # 7. Spotify
        if "spotify" in sender or "spotify" in combined.lower():
            m_amount = re.search(r"(?:total\s+charged|total|price)[\s:]*(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{2})?)", combined, re.IGNORECASE)
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    return TransactionCandidate(
                        merchant="Spotify",
                        amount=amt,
                        currency="INR",
                        date=fallback_date,
                        category="Subscriptions",
                        transaction_type="subscription",
                        confidence=0.99,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=True,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "spotify"},
                    )

        # 8. Google One / Google Play
        if "google" in sender and ("google one" in combined.lower() or "google play" in combined.lower()):
            m_amount = re.search(r"(?:total|price)[\s:]*(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{2})?)", combined, re.IGNORECASE)
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    return TransactionCandidate(
                        merchant="Google One",
                        amount=amt,
                        currency="INR",
                        date=fallback_date,
                        category="Subscriptions",
                        transaction_type="subscription",
                        confidence=0.98,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=True,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "google_one"},
                    )

        # 9. Adobe
        if "adobe" in sender or "adobe" in combined.lower():
            m_amount = re.search(
                r"(?:total\s+amount\s+charged|total)[\s:]*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)",
                combined,
                re.IGNORECASE,
            )
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    m_date = re.search(r"date[\s:]*([^\n\r]+)", body, re.IGNORECASE)
                    txn_date = _parse_date_safe(m_date.group(1), fallback_date) if m_date else fallback_date
                    return TransactionCandidate(
                        merchant="Adobe",
                        amount=amt,
                        currency="INR",
                        date=txn_date,
                        category="Subscriptions",
                        transaction_type="subscription",
                        confidence=0.99,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        is_recurring=True,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "adobe"},
                    )

        # 10. Airtel Broadband
        if "airtel" in sender or "airtel" in combined.lower():
            m_amount = re.search(
                r"(?:total\s+amount\s+due|bill\s+amount)[\s:]*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)",
                combined,
                re.IGNORECASE,
            )
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    # Look for due date
                    m_due = re.search(r"(?:due\s+date|payment\s+due\s+date)[\s:]*([^\n\r,]+)", combined, re.IGNORECASE)
                    due_date = _parse_date_safe(m_due.group(1), fallback_date) if m_due else None
                    return TransactionCandidate(
                        merchant="Airtel",
                        amount=amt,
                        currency="INR",
                        date=fallback_date,
                        category="Utilities",
                        transaction_type="bill",
                        confidence=0.98,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        due_date=due_date,
                        is_recurring=True,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "airtel"},
                    )

        # 11. BESCOM Electricity
        if "bescom" in sender or "bescom" in combined.lower():
            m_amount = re.search(
                r"(?:total\s+payable\s+amount|bill\s+for[^\n\r:]*:[\s]*rs\.?|total)[\s:]*(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{2})?)",
                combined,
                re.IGNORECASE,
            )
            if m_amount:
                amt = _parse_amount(m_amount.group(1))
                if amt:
                    m_due = re.search(r"(?:due\s+date|pay\s+by)[\s:]*([^\n\r,]+)", combined, re.IGNORECASE)
                    due_date = _parse_date_safe(m_due.group(1), fallback_date) if m_due else None
                    return TransactionCandidate(
                        merchant="BESCOM",
                        amount=amt,
                        currency="INR",
                        date=fallback_date,
                        category="Utilities",
                        transaction_type="bill",
                        confidence=0.97,
                        source_message_id=email.message_id,
                        source_subject=email.subject,
                        source_sender=email.sender,
                        due_date=due_date,
                        is_recurring=True,
                        raw_extraction_metadata={"extractor": "regex", "vendor": "bescom"},
                    )

        # 12. Generalized Structured Invoice/Receipt Pattern (e.g. Apex Cloud Services, etc.)
        m_invoice = re.search(
            r"(?:total\s+invoice\s+amount|grand\s+total|total\s+paid|total\s+amount|amount\s+paid)[\s:]*(?:rs\.?|inr|₹|\$)\s*([\d,]+(?:\.\d{2})?)",
            combined,
            re.IGNORECASE,
        )
        if m_invoice:
            amt = _parse_amount(m_invoice.group(1))
            if amt:
                # Infer merchant from sender domain or header
                merchant = cls._infer_merchant(email)
                category = cls._infer_category(combined)
                return TransactionCandidate(
                    merchant=merchant,
                    amount=amt,
                    currency="INR",
                    date=fallback_date,
                    category=category,
                    transaction_type="bill" if "invoice" in combined.lower() else "purchase",
                    confidence=0.91,
                    source_message_id=email.message_id,
                    source_subject=email.subject,
                    source_sender=email.sender,
                    is_recurring=False,
                    raw_extraction_metadata={"extractor": "regex", "vendor": "generalized"},
                )

        return None

    @classmethod
    def _infer_merchant(cls, email: EmailMessage) -> str:
        """Heuristically derive merchant name from sender header or subject."""
        # E.g. 'Apex Cloud Services Pvt Ltd <invoicing@apexcloud.io>'
        sender = email.sender
        if "<" in sender:
            display_name = sender.split("<")[0].strip().replace('"', "")
            if display_name and len(display_name) > 2:
                return display_name.split()[0] + (" " + display_name.split()[1] if len(display_name.split()) > 1 else "")
        domain_match = re.search(r"@([a-zA-Z0-9.-]+)", sender)
        if domain_match:
            parts = domain_match.group(1).split(".")
            name = parts[0] if parts[0] not in ("mail", "mailer", "alerts", "invoicing") else parts[1]
            return name.capitalize()
        return "Unknown Merchant"

    @classmethod
    def _infer_category(cls, text: str) -> CategoryType:
        """Heuristic category classification."""
        lower = text.lower()
        if any(w in lower for w in ("cloud", "server", "compute", "hosting", "electricity", "broadband", "power", "utility")):
            return "Utilities"
        if any(w in lower for w in ("food", "restaurant", "meal", "biryani", "pizza", "dining")):
            return "Food"
        if any(w in lower for w in ("trip", "ride", "flight", "taxi", "cab", "hotel")):
            return "Travel"
        if any(w in lower for w in ("subscription", "membership", "monthly plan", "renewal")):
            return "Subscriptions"
        if any(w in lower for w in ("shoe", "cloth", "earbud", "amazon", "flipkart", "cart")):
            return "Shopping"
        return "Other"
