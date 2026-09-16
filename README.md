# Polarisk Gmail Spend Intelligence

> **Enterprise-Grade Financial Intelligence Pipeline Extracting, Validating, and Analyzing Transaction Telemetry from Gmail.**  
> *Core Principle: AI interprets messy data; deterministic systems establish financial facts.*

---

## Executive Overview
Most personal finance management tools force manual data entry or complete bank statement scraping. Gmail contains extensive transactional telemetry (e-commerce invoices, ride receipts, SaaS subscriptions, utility bills), but email bodies are heterogeneous, unstructured, and noisy.

A naive LLM-only pipeline (Email $\rightarrow$ LLM $\rightarrow$ Numbers) suffers from numerical hallucinations, privacy leakage, failure on empty inboxes, high latency, and excessive API costs.

**Polarisk Gmail Spend Intelligence** resolves this through an enterprise dual-mode pipeline:
1. **Minimal-Scope Google OAuth 2.0**: Ingests headers and transactional bodies under strictly read-only (`https://www.googleapis.com/auth/gmail.readonly`) permissions with zero modification to user mailboxes.
2. **Dual Execution Modes**: Seamless switching between **Mode A (Live Gmail OAuth)** and **Mode B (Synthetic Demo Dataset)** containing 18+ rich edge-case scenarios (price spikes, new vendors, refunds, duplicates, and non-financial noise).
3. **Hybrid Extraction Engine**: Ultra-fast deterministic regex parsers for high-volume vendors (Amazon, Swiggy, Uber, etc.) paired with structured Gemini 1.5 Flash fallback.
4. **Deterministic Pydantic v2 Contracts**: Enforces `confidence >= 0.85`, positive amounts, ISO dates, and strict category boundaries.
5. **Deterministic Analytics**: Totals, recurring cadences, and category distributions computed mathematically with Pandas (never by an LLM).
6. **Statistical Anomaly Engine**: Detects price jumps (>20% baseline), first-time high-spend merchants (>₹10,000), and upcoming bill renewal notices.
7. **AI-Assisted Natural Language Explanations**: Grounded Gemini 1.5 Flash explanations contextualizing why anomalies were flagged.
8. **Full Email Traceability & Clean Empty States**: Trace transactions back to source message IDs with full audit modal and zero-data empty states.

---

## System Architecture

```
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
       - Regex Fast-Path (Amazon, Uber, Swiggy)        (No spending data found)
       - Gemini Flash Structured Fallback
                   |
                   v
       [Pydantic Schema Validation]
       (Amount > 0, Currency, Date ISO,
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
```

---

## Repository Structure

```
polarisk-gmail-spend-intelligence/
├── .env.example
├── .gitignore
├── pyproject.toml
├── README.md
├── requirements.txt
├── TASK.md
├── demo_data/
│   └── synthetic_emails.json
├── src/
│   ├── analytics/
│   ├── anomaly/
│   ├── auth/
│   ├── extraction/
│   ├── ingestion/
│   └── ui/
└── tests/
```

---

## Security & Privacy Non-Negotiables
- **Strict Read-Only Scope**: `https://www.googleapis.com/auth/gmail.readonly` only.
- **Zero In-Box Modifications**: Never send, mark, trash, or label emails.
- **In-Memory Processing**: User emails are parsed ephemerally and never written to permanent external databases.
- **Zero Secrets**: Credentials and tokens are git-ignored.
