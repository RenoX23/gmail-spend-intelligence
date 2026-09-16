"""Hybrid Extraction Engine combining deterministic Regex with Gemini 1.5 Flash fallback.

Architecture:
    Raw Emails -> Candidate Relevance Filter
               -> Regex Fast-Path (sub-millisecond)
               -> Gemini 1.5 Flash Fallback (structured JSON)
               -> Pydantic v2 Schema Gate (confidence >= 0.85, amount > 0)
               -> Deduplicator
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, NamedTuple, Optional

from src.extraction.deduplicator import TransactionDeduplicator
from src.extraction.gemini_extractor import GeminiExtractor
from src.extraction.regex_extractors import RegexVendorExtractor
from src.ingestion.candidate_filter import CandidateFilter
from src.schemas import EmailMessage, Transaction, TransactionCandidate


class ExtractionPipelineResult(NamedTuple):
    transactions: List[Transaction]
    filtered_out_noise: List[EmailMessage]
    rejected_extractions: List[Dict[str, Any]]
    duplicates_detected: List[Dict[str, str]]


class HybridExtractionEngine:
    """Orchestrator for financial telemetry extraction."""

    def __init__(self, gemini_api_key: Optional[str] = None) -> None:
        self.gemini_extractor = GeminiExtractor(api_key=gemini_api_key)

    def process_emails(self, emails: List[EmailMessage]) -> ExtractionPipelineResult:
        """Run complete extraction, validation, and deduplication pipeline."""
        # 1. Candidate relevance filter
        candidates, noise = CandidateFilter.filter_batch(emails)

        raw_candidates: List[TransactionCandidate] = []
        rejected_extractions: List[Dict[str, Any]] = []

        for email in candidates:
            # 2. Fast-path regex parser
            candidate = RegexVendorExtractor.extract(email)

            # 3. Gemini fallback if regex yields no extraction
            if candidate is None and self.gemini_extractor.is_available():
                candidate = self.gemini_extractor.extract(email)

            if candidate is None or candidate.amount is None or candidate.amount <= 0:
                rejected_extractions.append({
                    "message_id": email.message_id,
                    "subject": email.subject,
                    "reason": "Missing or non-positive numerical amount in body text",
                })
                continue

            raw_candidates.append(candidate)

        # 4. Pydantic schema validation & confidence gating (>= 0.85)
        validated_txns: List[Transaction] = []
        for cand in raw_candidates:
            if cand.confidence < 0.85:
                rejected_extractions.append({
                    "message_id": cand.source_message_id,
                    "subject": cand.source_subject,
                    "reason": f"Confidence score {cand.confidence:.2f} failed production threshold of 0.85",
                })
                continue

            # Deterministic transaction ID
            txn_hash_input = f"{cand.merchant}_{cand.amount:.2f}_{cand.date}_{cand.source_message_id}"
            txn_id = f"txn_{hashlib.md5(txn_hash_input.encode('utf-8')).hexdigest()[:12]}"

            try:
                txn = Transaction(
                    transaction_id=txn_id,
                    merchant=cand.merchant,
                    amount=cand.amount,
                    currency=cand.currency,
                    date=cand.date,
                    category=cand.category,
                    transaction_type=cand.transaction_type,
                    confidence=cand.confidence,
                    source_message_id=cand.source_message_id,
                    source_subject=cand.source_subject,
                    source_sender=cand.source_sender,
                    due_date=cand.due_date,
                    is_recurring=cand.is_recurring,
                )
                validated_txns.append(txn)
            except Exception as e:
                rejected_extractions.append({
                    "message_id": cand.source_message_id,
                    "subject": cand.source_subject,
                    "reason": f"Pydantic validation failed: {str(e)}",
                })

        # 5. Deduplication
        dedup_result = TransactionDeduplicator.deduplicate(validated_txns)

        return ExtractionPipelineResult(
            transactions=dedup_result.unique_transactions,
            filtered_out_noise=noise,
            rejected_extractions=rejected_extractions,
            duplicates_detected=dedup_result.duplicate_records,
        )
