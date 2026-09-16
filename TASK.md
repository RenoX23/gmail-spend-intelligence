# Polarisk Technical Task - Gmail Spend Intelligence

> **Company**: Beyond Technologies  
> **Role**: AI Engineer Intern  
> **Task**: Technical Task - Gmail Spend Intelligence  
> **Core Principle**: *AI interprets messy data; deterministic systems establish financial facts.*  

---

## 1. Problem Statement & Executive Framing
Most financial tracking tools require manual entry or full bank statement uploads. Gmail contains rich transactional telemetry (e-commerce invoices, ride receipts, SaaS subscriptions, utility bills), but email bodies are messy, heterogeneous, unstructured, and noisy.

A naive LLM-only approach (Gmail -> LLM -> Numbers) hallucinates amounts, violates privacy, fails on empty states, and incurs high latency and cost. 

This project implements an **enterprise-grade, production financial intelligence pipeline**:
1. **Minimal-Scope Ingestion**: Google OAuth 2.0 using strictly read-only permissions (gmail.readonly), retrieving only candidate financial headers without modifying user inboxes.
2. **Dual Execution Modes**:
   - **Mode A (Live Gmail)**: Authenticates user, fetches permitted emails, filters candidates, and extracts spending.
   - **Mode B (Synthetic Demo Dataset)**: Bundles a robust suite of 18+ edge-case synthetic emails (price hikes, new merchants, recurring cadences, refunds, duplicates, and non-financial noise) allowing evaluators to audit the full pipeline instantly with zero OAuth setup.
3. **Deterministic Validation & Schema Integrity**: Extracted payloads are validated through **Pydantic v2** models with confidence scoring. Unverified or ambiguous amounts are rejected from aggregations.
4. **Deterministic Analytics & Statistical Anomaly Detection**: Totals, categories, and recurring subscriptions are computed deterministically in code (not by an LLM). Statistical anomalies (Z-score price hikes, new merchant flags, upcoming renewal notices) are computed mathematically.
5. **AI-Assisted Natural Language Explanations**: Gemini 1.5 Flash generates plain-English, evidence-grounded explanations explaining why an anomaly was flagged.
6. **Full Email Traceability**: Every transaction and alert links back to its originating source_message_id and subject line.

---

## 2. System Architecture & Data Flow

`
                  +----------------------+   +----------------------+
                  | Mode 1: Live Gmail   |   | Mode 2: Demo Dataset |
                  | (Google OAuth 2.0)   |   | (18+ Synthetic Cases)|
                  +----------+-----------+   +----------+-----------+
                             |                          |
                             +------------+-------------+
                                          |
                                          v
                         [Candidate Relevance Filter]
                         (Subject, sender, keyword rules)
                                          |
                   +----------------------+----------------------+
                   |                                             |
                   v                                             v
          [Financial Emails]                           [No Financial Emails]
                   |                                             |
                   v                                             v
       [Hybrid Extraction Engine]                      [Polished Empty State]
       - Regex Fast-Path (Amazon, Uber)                ( No spending data found)
       - Gemini Flash Structured Fallback
                   |
                   v
       [Pydantic Schema Validation]
       (Amount != Null, Currency, Date ISO,
        Confidence Score >= 0.85, Deduplication)
                   |
                   v
       [Deterministic Analytics Layer (Pandas)]
       - Total Spend, Category Breakdown, Merchant Ranks
       - Recurring Cadence Detection (Monthly, Annual)
                   |
                   v
       [Statistical Anomaly & Attention Detector]
       - Price Jumps (>20% baseline)
       - New Merchant (>Rs 10,000 never seen before)
       - Upcoming Renewal / Due Dates
                   |
                   v
       [AI Natural-Language Explanation Layer]
       (Gemini Flash generating fact-grounded rationale)
                   |
                   v
       [Interactive Streamlit Fintech Dashboard]
       - Overview KPI Cards & Interactive Plotly Charts
       - Alerts Center with [View Source Email] Traceability Modal
`

---

## 3. Core Data Schemas (Pydantic v2)

`python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date

class Transaction(BaseModel):
    transaction_id: str
    merchant: str
    amount: float = Field(gt=0, description=Transaction amount in specified currency)
    currency: str = Field(default=INR)
    date: date
    category: Literal[Shopping, Travel, Food, Subscriptions, Utilities, Other]
    transaction_type: Literal[purchase, subscription, bill, refund]
    confidence: float = Field(ge=0.0, le=1.0)
    source_message_id: str
    source_subject: str
    source_sender: str
    due_date: Optional[date] = None
    is_recurring: bool = False

class AnomalyAlert(BaseModel):
    alert_id: str
    alert_type: Literal[price_increase, new_merchant, upcoming_renewal, unusual_amount]
    severity: Literal[low, medium, high]
    merchant: str
    amount: float
    explanation: str
    source_message_id: str
`

---

## 4. Phased Build Roadmap & Git Commit Milestones

### Phase 1: Synthetic Demo Dataset & Data Schemas
* **Deliverable**: Comprehensive 18-email synthetic JSON test suite in demo_data/ covering:
  1. Normal purchases (Amazon Rs 2,499, Swiggy Rs 620)
  2. Subscriptions (Netflix Rs 649, Spotify Rs 119)
  3. Price hikes (Adobe Rs 6,899 vs previous Rs 5,499)
  4. Large anomalous merchant (Apex Cloud Services Rs 35,000)
  5. Missing amounts (Payment confirmation with no amount)
  6. Duplicate emails (Same order received twice)
  7. Refunds (Amazon refund Rs 1,299)
  8. Upcoming renewals (Adobe renewing tomorrow)
  9. Non-financial noise (College announcement, newsletter)
* **Acceptance Criteria**: Pydantic models validate clean transactions and reject invalid edge cases; automated test suite passes.
* **Commit**: eat(data): create 18-case synthetic demo dataset and pydantic transaction schemas

### Phase 2: Scoped Gmail Retrieval & Dual-Mode Ingestion Engine
* **Deliverable**: Google OAuth 2.0 handler with minimal gmail.readonly scope + query filter (has:attachment OR invoice OR receipt OR payment OR bill) + Dual-Mode interface.
* **Acceptance Criteria**: App toggles seamlessly between Live Gmail OAuth and Demo Dataset without breaking state.
* **Commit**: eat(ingestion): build dual-mode loader with google oauth and candidate relevance filter

### Phase 3: Hybrid Extraction, Normalization & Deduplication
* **Deliverable**: High-speed Regex parsers for top vendors + Gemini 1.5 Flash structured JSON extractor fallback for non-standard formats + MD5/composite key deduplication.
* **Acceptance Criteria**: Accurately parses receipts, rejects ambiguous amounts without hallucinating, and assigns confidence scores.
* **Commit**: eat(extraction): implement hybrid regex-LLM extraction with pydantic validation and deduplication

### Phase 4: Deterministic Analytics & Statistical Anomaly Engine
* **Deliverable**: Pandas aggregation pipeline (totals, categories, merchants, recurring cadences) + statistical anomaly engine detecting:
  - Price jumps (>20% over 3-month merchant average)
  - First-time high-spend merchants (>Rs 10,000)
  - Upcoming renewal alerts based on explicit email due dates
* **Acceptance Criteria**: Zero hallucinated spending; mathematical checks verified against ground-truth dataset.
* **Commit**: eat(analytics): implement deterministic spend analytics and statistical anomaly detection

### Phase 5: Interactive Streamlit Fintech Dashboard & Traceability
* **Deliverable**: Polished dark-mode Streamlit dashboard featuring:
  - KPI Overview Cards (Total Spend, Top Category, Top Merchant)
  - Monthly spending trends (Plotly line/bar charts)
  - Recurring subscription monitor
  - Attention Required (Alerts Center with AI explanations)
  - **View Source Email Modal / Drawer** showing original message headers and body excerpt
  - **Explicit Empty State** for inboxes with 0 financial emails
* **Acceptance Criteria**: Full UI renders smoothly in <1 second; trace buttons display source email context.
* **Commit**: eat(ui): complete polished streamlit dashboard with email traceability and empty states

### Phase 6: Production Documentation & Cloud Deployment
* **Deliverable**: Exhaustive README.md fulfilling all Section 32 requirements + Streamlit Cloud deployment with public HTTPS URL.
* **Acceptance Criteria**: Live demo URL accessible 24/7; README passes evaluator rubric.
* **Commit**: docs(readme): finalize production architecture, security disclosures, and deployment guides

---

## 5. Security & Privacy Constraints (Non-Negotiable)
1. **Minimal OAuth Scope**: Request *only* https://www.googleapis.com/auth/gmail.readonly.
2. **Zero Modification**: No delete, send, mark-as-read, or label modifications.
3. **No Secret Leaks**: Never commit credentials.json, 	oken.json, or .env.
4. **Data Ephemerality**: User emails are processed in-memory during the session and never stored in an external permanent database.

---

## 6. Submission Deliverables Checklist
* **Link 1**: GitHub Repository (Clean commit history, test coverage, comprehensive README).
* **Link 2**: Live Deployed Application on Streamlit Cloud (with functional Try Demo Data mode).
* **Link 3**: 3-minute Loom / YouTube demo video walking through OAuth, Demo mode, Anomalies, and Traceability.
