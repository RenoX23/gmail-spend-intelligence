"""High-performance candidate relevance filter for financial emails.

Core principle:
    Deterministic rule-based pre-filter separating candidate financial telemetry
    from non-financial noise (newsletters, social notifications, campus notices, marketing).
"""

from __future__ import annotations

import re
from typing import List, NamedTuple, Tuple

from src.schemas import EmailMessage


class FilterResult(NamedTuple):
    is_financial: bool
    confidence: float
    matched_signals: List[str]
    rejection_reason: str


class CandidateFilter:
    """Pre-filters raw emails before computationally expensive extraction pipelines."""

    # Explicit negative signals that immediately disqualify an email unless strong invoice keywords exist
    NOISE_PATTERNS = [
        re.compile(r"\b(campus\s+recruitment|placement\s+office|dean\s+of|placement\s+portal)\b", re.IGNORECASE),
        re.compile(r"\b(weekly\s+digest|weekly\s+newsletter|issue\s+\d+|daily\s+digest)\b", re.IGNORECASE),
        re.compile(r"\b(profile\s+views|appeared\s+in\s+\d+\s+searches|connection\s+requests?)\b", re.IGNORECASE),
        re.compile(r"\b(who\s+viewed\s+your\s+profile|grow\s+your\s+network|join\s+my\s+network)\b", re.IGNORECASE),
        re.compile(r"\b(webinar\s+invitation|free\s+trial\s+expires\s+in|marketing\s+update)\b", re.IGNORECASE),
    ]

    # Explicit financial signal keywords in subject or body
    FINANCIAL_SUBJECT_KEYWORDS = [
        re.compile(r"\b(tax\s+invoice|invoice\s*#?|tax\s+bill|e-?bill)\b", re.IGNORECASE),
        re.compile(r"\b(receipt\s*#?|trip\s+receipt|payment\s+receipt|order\s+receipt|your\s+receipt)\b", re.IGNORECASE),
        re.compile(r"\b(order\s+confirmation|ordered:|confirmation\s+for\s+your\s+order)\b", re.IGNORECASE),
        re.compile(r"\b(membership\s+renewed|subscription\s+(?:renewed|receipt|invoice|membership))\b", re.IGNORECASE),
        re.compile(r"\b(refund\s+confirmation|refund\s+processed|credit\s+note)\b", re.IGNORECASE),
        re.compile(r"\b(bill\s+notice|electricity\s+bill|broadband\s+bill|statement)\b", re.IGNORECASE),
        re.compile(r"\b(payment\s+received|payment\s+successful|charged|debited|transaction\s+alert)\b", re.IGNORECASE),
        re.compile(r"\b(auto-?debit\s+mandate|e-?mandate)\b", re.IGNORECASE),
    ]

    # Structural body signals indicating monetary settlement
    FINANCIAL_BODY_PATTERNS = [
        re.compile(r"(?:total\s+(?:amount\s+)?(?:due|payable|paid)|grand\s+total|subtotal)[\s:]*(?:rs\.?|inr|₹|\$)\s*[\d,]+(?:\.\d{2})?", re.IGNORECASE),
        re.compile(r"(?:rs\.?|inr|₹|\$)\s*[\d,]+(?:\.\d{2})?\s*(?:has\s+been\s+(?:debited|charged|refunded|credited))", re.IGNORECASE),
        re.compile(r"\b(?:invoice\s*#?|order\s*#?|bill\s+date|due\s+date|gstin|cgst|sgst|igst)\b", re.IGNORECASE),
    ]

    # Known high-confidence transactional sender patterns
    TRANSACTIONAL_SENDER_PATTERNS = [
        re.compile(r"(?:auto-confirm|ship-confirm|payments-update|order-update)@amazon\.", re.IGNORECASE),
        re.compile(r"(?:orders|support)@swiggy\.", re.IGNORECASE),
        re.compile(r"uber\.(?:india|com)@uber\.com", re.IGNORECASE),
        re.compile(r"(?:order-update|noreply)@flipkart\.com", re.IGNORECASE),
        re.compile(r"mailer\.netflix\.com|spotify\.com|googleplay-noreply@google\.com", re.IGNORECASE),
        re.compile(r"billing@adobe\.com|ebill@airtel\.com|bescom", re.IGNORECASE),
        re.compile(r"\b(?:billing|invoicing|receipts|orders|payments|alerts)@", re.IGNORECASE),
    ]

    @classmethod
    def evaluate(cls, email: EmailMessage) -> FilterResult:
        """Evaluate an EmailMessage and return whether it is a financial candidate."""
        subject = email.subject or ""
        body = email.body_text or ""
        sender = email.sender or ""
        snippet = email.snippet or ""
        combined_text = f"{subject}\n{snippet}\n{body[:1000]}"

        matched_signals: List[str] = []

        # Check noise patterns first
        for noise_pat in cls.NOISE_PATTERNS:
            if noise_pat.search(subject) or noise_pat.search(snippet):
                return FilterResult(
                    is_financial=False,
                    confidence=0.99,
                    matched_signals=["negative_noise_match"],
                    rejection_reason=f"Matched non-financial noise pattern: {noise_pat.pattern}",
                )

        # Check transactional sender
        is_known_sender = False
        for sender_pat in cls.TRANSACTIONAL_SENDER_PATTERNS:
            if sender_pat.search(sender):
                is_known_sender = True
                matched_signals.append(f"known_sender:{sender_pat.pattern}")
                break

        # Check subject signals
        has_financial_subject = False
        for subj_pat in cls.FINANCIAL_SUBJECT_KEYWORDS:
            if subj_pat.search(subject):
                has_financial_subject = True
                matched_signals.append(f"subject_signal:{subj_pat.pattern}")
                break

        # Check body structure signals
        has_body_signal = False
        for body_pat in cls.FINANCIAL_BODY_PATTERNS:
            if body_pat.search(combined_text):
                has_body_signal = True
                matched_signals.append(f"body_signal:{body_pat.pattern}")
                break

        # Decision synthesis
        if has_financial_subject or (is_known_sender and has_body_signal):
            confidence = 0.95 if (has_financial_subject and has_body_signal) else 0.88
            return FilterResult(
                is_financial=True,
                confidence=confidence,
                matched_signals=matched_signals,
                rejection_reason="",
            )

        if has_body_signal:
            return FilterResult(
                is_financial=True,
                confidence=0.85,
                matched_signals=matched_signals,
                rejection_reason="",
            )

        return FilterResult(
            is_financial=False,
            confidence=0.90,
            matched_signals=matched_signals,
            rejection_reason="No transactional keywords or monetary amounts detected",
        )

    @classmethod
    def filter_batch(cls, emails: List[EmailMessage]) -> Tuple[List[EmailMessage], List[EmailMessage]]:
        """Partition batch into (financial_candidates, discarded_noise)."""
        candidates: List[EmailMessage] = []
        discarded: List[EmailMessage] = []

        for email in emails:
            result = cls.evaluate(email)
            if result.is_financial:
                candidates.append(email)
            else:
                discarded.append(email)

        return candidates, discarded
