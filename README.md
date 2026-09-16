# Polarisk Gmail Spend Intelligence

> **Enterprise-grade telemetry pipeline extracting, validating, and analyzing transaction data from consumer Gmail inboxes.**  
> *Core Architectural Axiom: AI interprets messy, unstructured data; deterministic systems establish immutable financial facts.*

[![Live App](https://img.shields.io/badge/Live%20App-Streamlit%20Cloud-FF4B4B.svg?style=flat&logo=streamlit)](https://renox23-gmail-spend-intelligence.streamlit.app/)
[![Video Walkthrough](https://img.shields.io/badge/Demo%20Video-Google%20Drive-4285F4.svg?style=flat&logo=googledrive)](https://drive.google.com/file/d/1rU84U0IHJBs2suP_exyno8SoLikEvO27/view?usp=sharing)
[![Tests Passing](https://img.shields.io/badge/Tests-51%20Passed-10b981.svg)](tests/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.13-E92063.svg)](https://docs.pydantic.dev/)
[![LLMs](https://img.shields.io/badge/LLM-Gemini%20Flash%20%7C%20Groq%20Llama--3.3-orange.svg)](https://groq.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Project Deliverables

| Deliverable | Link | Description |
|---|---|---|
| 🌐 **Live Cloud Application** | [renox23-gmail-spend-intelligence.streamlit.app](https://renox23-gmail-spend-intelligence.streamlit.app/) | Deployed on Streamlit Cloud. Instant Mode B evaluation with 18+ synthetic edge cases. |
| 🎬 **Demo Video Walkthrough** | [Google Drive Video Demo](https://drive.google.com/file/d/1rU84U0IHJBs2suP_exyno8SoLikEvO27/view?usp=sharing) | End-to-end walkthrough of Google OAuth, live inbox extraction, and anomaly telemetry. |
| 💻 **GitHub Repository** | [github.com/RenoX23/gmail-spend-intelligence](https://github.com/RenoX23/gmail-spend-intelligence) | Complete open-source pipeline with 51 automated unit and integration tests. |

---

## 1. Executive Summary & Problem Framing

Transactional telemetry (e-commerce receipts, rides, food delivery, recurring bills, SaaS subscriptions) is scattered across consumer inboxes in noisy, heterogeneous formats. 

Piping raw inboxes directly into an LLM (`Inbox -> LLM -> Numbers`) introduces **hallucinated totals**, **astronomical token costs**, and **privacy leaks**.

**Polarisk decouples probabilistic extraction from deterministic financial aggregation:**
1. **Scoped Ingestion**: Connects via Google OAuth 2.0 with strictly read-only access (`gmail.readonly`).
2. **Hybrid Extraction**: Sub-millisecond regex fast-paths parse >80% of standard receipts (Amazon, Swiggy, Uber, Netflix); zero-temperature LLMs (**Gemini 1.5 Flash** or **Groq Llama-3.3-70B**) act as structured fallbacks.
3. **Data Contract Enforcement**: All transactions are validated through **Pydantic v2** (`amount > 0`, ISO date, currency normalization, `confidence >= 0.85`).
4. **Deterministic Analytics**: Net spend, run-rates, category totals, and subscription cadences are computed in **Pandas**—never hallucinated by an LLM.
5. **Statistical Anomaly Detection**: Mathematical detection of subscription price spikes (>20%), high-spend new merchants (>₹10,000), and renewal deadlines.
6. **Complete Audit Provenance**: Every transaction links back to its original `source_message_id`, sender, date, and raw email body.

---

## 2. End-to-End Architecture

```
                          +-----------------------------------+
                          |        User Execution Mode        |
                          +-----------------+-----------------+
                                            |
                  +-------------------------+-------------------------+
                  v                                                   v
   +------------------------------+                    +------------------------------+
   |   Mode A: Live Gmail OAuth   |                    |   Mode B: Synthetic Demo     |
   | - Google OAuth 2.0           |                    | - 18+ Production Edge Cases  |
   | - Scope: gmail.readonly only |                    | - Price hikes, refunds, dups |
   | - Ephemeral session memory   |                    | - Campus noise, missing sums |
   +--------------+---------------+                    +--------------+---------------+
                  |                                                   |
                  +-------------------------+-------------------------+
                                            v
                             [Candidate Relevance Filter]
                       (Filters newsletters, invites, spam)
                                            |
                                            v
                             [Hybrid Extraction Engine]
                     1. Sub-ms Regex Fast-Path (Amazon, Uber)
                     2. LLM Fallback (Gemini Flash / Groq)
                                            |
                                            v
                             [Pydantic v2 Schema Gate]
                     - amount > 0, currency normalization
                     - Cryptographic & Order ID deduplication
                                            |
                                            v
                           [Deterministic Analytics (Pandas)]
                     - Net Spend, Category Shares, Subscriptions
                                            |
                                            v
                            [Statistical Anomaly Engine]
                     - Price Spikes (>20% baseline jump)
                     - First-Time High-Spend Vendors (>₹10K)
                     - Upcoming Renewal Due Dates (<=7 days)
                                            |
                                            v
                            [Streamlit Fintech Dashboard]
                     - Executive KPIs & Plotly visual charts
                     - Evidence-grounded natural language context
                     - Full Source Email Traceability Drawer
```

---

## 3. Dual Execution Modes

### Mode A: Live Gmail OAuth (Read-Only)
* Connects securely using **Google OAuth 2.0** with strictly `https://www.googleapis.com/auth/gmail.readonly`.
* Scans candidate query (`has:attachment OR invoice OR receipt OR payment OR bill OR statement`).
* Zero email modification, zero external persistence. Processing runs in-memory.

### Mode B: Synthetic Demo Dataset (18+ Edge Cases)
Pre-packaged with 21 realistic test emails in `demo_data/synthetic_emails.json` enabling instant evaluation without requiring Google credentials:
* **Standard Receipts**: Amazon India (₹2,499.00), Flipkart (₹1,899.00), Swiggy (₹620.00), Uber (₹435.50).
* **Subscriptions**: Netflix (₹649/mo), Spotify (₹119/mo), Google One (₹130/mo).
* **Price Spike Anomaly**: Adobe Creative Cloud (₹5,499 $\rightarrow$ ₹5,499 $\rightarrow$ ₹6,899) $\rightarrow$ **+25.46% hike flagged as High-Severity**.
* **First-Time High Spend**: Apex Cloud Services (₹35,000.00 GPU cluster) $\rightarrow$ **Flagged over ₹10,000 threshold**.
* **Upcoming Renewal Alerts**: Airtel Broadband (due in 2 days) and BESCOM Electricity (due in 3 days).
* **Refund Subtraction**: Amazon return credit (₹1,299.00) $\rightarrow$ Deterministically subtracted from gross spend.
* **Duplicate Detection**: Identical order confirmations $\rightarrow$ Suppressed via cryptographic hash & order ID.
* **Noise Rejection**: Campus recruitment, LinkedIn updates, and newsletters filtered before extraction.
* **Missing Amount Guard**: Auto-debit notices lacking numerical values $\rightarrow$ Quarantined without hallucination.

---

## 4. Statistical Anomaly Detection Formulas

Rather than delegating risk analysis to probabilistic AI, Polarisk calculates anomalies deterministically:

1. **Subscription Price Hike**:
   $$\Delta\% = \frac{\text{Current Charge} - \overline{\text{Historical Baseline}}}{\overline{\text{Historical Baseline}}} \times 100 \quad (\ge 20\% \implies \text{Alert})$$
2. **First-Time High-Spend Vendor**:
   $$\text{Amount} \ge ₹10,000.00 \quad \land \quad \text{Prior Transaction History} = 0$$
3. **Upcoming Renewal Horizon**:
   $$\text{Due Date} - \text{Reference Date} \le 7 \text{ days}$$

---

## 5. Security & Privacy Guarantees

* 🔒 **Minimal Scope**: Hardcoded to `gmail.readonly`. The app cannot send, delete, or modify any email.
* 🛡️ **Zero Disk Persistence**: Raw emails and parsed tokens are held in ephemeral session memory.
* 🚫 **Secret Isolation**: `credentials.json`, `token.json`, and `.env` are strictly git-ignored.
* 🔍 **Full Audit Provenance**: Clicking **"🔍 Source Email"** on any transaction reveals the exact source subject, sender, date, and body text.

---

## 6. Quick-Start Guide

### Local Installation
```bash
# 1. Clone repository
git clone https://github.com/RenoX23/gmail-spend-intelligence.git
cd gmail-spend-intelligence

# 2. Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Configure LLM Key in .env
# Supports Google Gemini (AIza...) or Groq (gsk_...)
echo "GROQ_API_KEY=gsk_your_key_here" > .env

# 5. Launch dashboard
streamlit run app.py
```
Open `http://localhost:8501`. By default, the application runs on **Mode B**, rendering all 18+ test scenarios instantly.

---

## 7. Automated Testing Suite

All 51 automated unit, schema, and end-to-end tests run with Pytest:

```bash
pytest -v
```

```
tests/test_schemas.py ..........           [Validation contracts & amount gates]
tests/test_demo_dataset.py ...             [18+ edge case data integrity]
tests/test_candidate_filter.py ...         [Noise filtration & batch partitioning]
tests/test_extraction.py .............      [Regex fast-paths, deduplicator, LLM fallbacks]
tests/test_ingestion.py ....               [OAuth read-only verification & loader mocks]
tests/test_analytics.py .....              [Pandas spend metrics & cadence detection]
tests/test_anomaly.py .........            [Price spikes, new vendors, renewal windows]
tests/test_ui.py ......                    [Plotly visual charts & empty states]
tests/test_end_to_end.py .                 [Full end-to-end pipeline verification]

=========================== 51 passed in 3.90s ===========================
```

---

## 8. Engineering Design Decisions

| Decision | Alternative Considered | Why Polarisk Chose This Architecture |
|---|---|---|
| **Regex Fast-Path First** | LLM for every email | 80%+ of consumer receipts follow standard merchant templates. Regex runs in <0.5ms with 100% mathematical accuracy at zero API cost. |
| **Pandas for Analytics** | LLM aggregation prompts | LLMs hallucinate sums and misinterpret currency symbols. Pandas guarantees mathematically audited financial numbers. |
| **Pydantic v2 Gates** | Plain dictionaries / JSON | Strict data contracts with validation filters (`amount > 0`, ISO date, `confidence >= 0.85`) prevent corrupt data from reaching analytics. |
| **Dual-Mode Engine** | Live OAuth only | Allows recruiters and reviewers to audit 18+ real-world edge cases with zero credentials or GCP setup friction. |

---

## 9. Deliverables & Contact

* **Live App**: [renox23-gmail-spend-intelligence.streamlit.app](https://renox23-gmail-spend-intelligence.streamlit.app/)
* **Demo Video**: [Google Drive Video Walkthrough](https://drive.google.com/file/d/1rU84U0IHJBs2suP_exyno8SoLikEvO27/view?usp=sharing)
* **Author**: Renold Stephen ([GitHub: @RenoX23](https://github.com/RenoX23))
* **License**: MIT License
