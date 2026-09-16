"""Deduplication engine for financial email transactions.

Detects and suppresses duplicate transactions caused by:
1. Resent emails / duplicate invoice copies (same order/invoice ID)
2. Delivery updates and invoice attachments referencing same purchase
3. Composite collisions (merchant + exact amount + currency + date window)
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, NamedTuple, Optional, Set, Tuple

from src.schemas import Transaction


class DeduplicationResult(NamedTuple):
    unique_transactions: List[Transaction]
    duplicate_records: List[Dict[str, str]]


class TransactionDeduplicator:
    """Deterministic deduplication layer with provenance auditing."""

    # Patterns to extract explicit order/invoice reference numbers
    ORDER_ID_PATTERNS = [
        re.compile(r"order\s*#?\s*([0-9]{3}-[0-9]{7}-[0-9]{7})", re.IGNORECASE),  # Amazon format
        re.compile(r"order\s*(?:id|#)?[\s:]*([a-zA-Z0-9_-]{5,25})", re.IGNORECASE),
        re.compile(r"invoice\s*(?:id|#)?[\s:]*([a-zA-Z0-9_-]{4,25})", re.IGNORECASE),
        re.compile(r"receipt\s*#[\s:]*([a-zA-Z0-9_-]{4,25})", re.IGNORECASE),
        re.compile(r"ref\s*(?:id|#)?[\s:]*([a-zA-Z0-9_-]{4,25})", re.IGNORECASE),
    ]

    @classmethod
    def extract_order_reference(cls, text: str) -> Optional[str]:
        """Extract explicit order/invoice ID token if present."""
        for pattern in cls.ORDER_ID_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return None

    @classmethod
    def generate_transaction_hash(cls, txn: Transaction) -> str:
        """Create a deterministic unique hash for a transaction."""
        ref_id = cls.extract_order_reference(txn.source_subject)
        raw_key = f"{txn.merchant.lower()}_{txn.amount:.2f}_{txn.currency}_{txn.date.isoformat()}_{txn.transaction_type}_{ref_id or ''}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def deduplicate(cls, transactions: List[Transaction]) -> DeduplicationResult:
        """Filter out duplicates while maintaining audit trail."""
        seen_order_refs: Dict[str, str] = {}  # (merchant, ref_id) -> original_msg_id
        seen_composite_keys: Set[str] = set()

        unique: List[Transaction] = []
        duplicates: List[Dict[str, str]] = []

        for txn in transactions:
            # 1. Check explicit order/invoice reference
            order_ref = cls.extract_order_reference(txn.source_subject)
            if order_ref:
                merchant_ref_key = f"{txn.merchant.lower()}::{order_ref.lower()}"
                if merchant_ref_key in seen_order_refs:
                    duplicates.append({
                        "rejected_message_id": txn.source_message_id,
                        "original_message_id": seen_order_refs[merchant_ref_key],
                        "reason": f"Duplicate order/invoice reference '{order_ref}' for {txn.merchant}",
                        "merchant": txn.merchant,
                        "amount": str(txn.amount),
                    })
                    continue
                seen_order_refs[merchant_ref_key] = txn.source_message_id

            # 2. Check composite semantic key: merchant + amount + currency + date + type
            composite_key = f"{txn.merchant.lower()}::{txn.amount:.2f}::{txn.currency}::{txn.date.isoformat()}::{txn.transaction_type}"
            if composite_key in seen_composite_keys:
                duplicates.append({
                    "rejected_message_id": txn.source_message_id,
                    "original_message_id": "composite_match",
                    "reason": f"Identical transaction collision on {txn.date} for {txn.merchant} ({txn.currency} {txn.amount})",
                    "merchant": txn.merchant,
                    "amount": str(txn.amount),
                })
                continue

            seen_composite_keys.add(composite_key)
            unique.append(txn)

        return DeduplicationResult(
            unique_transactions=unique,
            duplicate_records=duplicates,
        )
