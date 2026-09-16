"""Polarisk Gmail Spend Intelligence - Interactive Streamlit Fintech Dashboard.

Core principle:
    AI interprets messy data; deterministic systems establish financial facts.
    Dual-mode: Live Gmail OAuth (read-only) + 18-case Synthetic Demo Dataset.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is in sys.path for direct Streamlit execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from src.analytics.cadence_detector import CadenceDetector
from src.analytics.spend_metrics import SpendMetricsCalculator
from src.anomaly.detector import AnomalyDetector
from src.anomaly.explainer import AnomalyExplainer
from src.auth.gmail_oauth import GmailOAuthHandler
from src.extraction.hybrid_engine import HybridExtractionEngine
from src.ingestion.demo_loader import DemoDatasetLoader
from src.ingestion.gmail_loader import LiveGmailLoader
from src.ui.charts import (
    create_category_donut_chart,
    create_monthly_trend_chart,
    create_top_merchants_chart,
)
from src.ui.components import (
    render_anomaly_card,
    render_empty_state,
    render_kpi_card,
    render_traceability_view,
)


# Page Configuration
st.set_page_config(
    page_title="Polarisk | Gmail Spend Intelligence",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
        .stApp {
            background-color: #0b0f19;
            color: #f1f5f9;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        div[data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        .stButton>button {
            border-radius: 8px;
            font-weight: 500;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_session_state() -> None:
    """Initialize persistent session variables."""
    if "pipeline_result" not in st.session_state:
        st.session_state["pipeline_result"] = None
    if "active_trace_msg_id" not in st.session_state:
        st.session_state["active_trace_msg_id"] = None
    if "emails_by_id" not in st.session_state:
        st.session_state["emails_by_id"] = {}


initialize_session_state()


# Sidebar Controls
with st.sidebar:
    st.markdown("### 💳 **Polarisk Intelligence**")
    st.caption("Gmail Transaction Telemetry Pipeline")
    st.markdown("---")

    st.markdown("#### **Execution Mode**")
    mode = st.radio(
        "Select Pipeline Source:",
        options=[
            "Mode B: Synthetic Demo Dataset (18+ Cases)",
            "Mode A: Live Gmail (OAuth 2.0 Read-Only)",
        ],
        index=0,
        help="Mode B allows instant evaluation of 18 edge cases (price hikes, noise, duplicates) with zero credentials.",
    )

    gemini_key = st.text_input(
        "LLM API Key (Gemini or Groq - Optional):",
        value=os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY") or "",
        type="password",
        help="Supports Google Gemini (AIza...) or Groq (gsk_...). Enables structured fallback extraction & natural language anomaly explanations.",
    )

    st.markdown("---")

    gmail_service = None
    client_secrets_path = "credentials.json"
    gmail_query = "has:attachment OR invoice OR receipt OR payment OR bill OR statement"
    max_emails = 50

    if "Live Gmail" in mode:
        st.markdown("#### **Google OAuth 2.0 Settings**")
        client_secrets_path = st.text_input("Client Secrets Path:", value="credentials.json")
        oauth_handler = GmailOAuthHandler(client_secrets_file=client_secrets_path)

        if not oauth_handler.is_configured():
            st.warning("⚠️ `credentials.json` not detected in project root.")
            with st.expander("ℹ️ How to get credentials.json (5 mins)", expanded=False):
                st.markdown(
                    """
                    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
                    2. Create project & enable **Gmail API**
                    3. Configure **OAuth Consent Screen** (User Type: External, add your email as Test User)
                    4. Create Credentials -> **OAuth Client ID** -> Type: **Desktop App**
                    5. Download JSON, rename to `credentials.json`, and place in project root.
                    """
                )
        else:
            user_email = oauth_handler.get_user_email()
            if user_email:
                st.success(f"✅ Connected: **{user_email}**")
                if st.button("🔄 Disconnect / Revoke", use_container_width=True):
                    oauth_handler.revoke_credentials()
                    st.session_state["pipeline_result"] = None
                    st.rerun()
            else:
                if st.button("🔑 Connect Google Account", use_container_width=True):
                    with st.spinner("Authorizing with Google OAuth... (check browser window)"):
                        try:
                            creds = oauth_handler.get_credentials(allow_browser_flow=True)
                            if creds:
                                st.rerun()
                        except Exception as e:
                            st.error(f"OAuth error: {e}")

        gmail_query = st.text_input(
            "Search Query Filter:",
            value="has:attachment OR invoice OR receipt OR payment OR bill OR statement",
        )
        max_emails = st.slider("Max Emails to Retrieve:", min_value=10, max_value=100, value=50, step=10)

    st.markdown("#### **Pipeline Execution**")
    run_pipeline = st.button("🚀 Run Spend Intelligence Pipeline", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size: 11.5px; color: #64748b; line-height: 1.6;">
            <b>Security & Privacy Guarantee:</b><br>
            • Scope: <code>gmail.readonly</code> only<br>
            • In-memory ephemeral processing<br>
            • Zero email modification or external storage<br>
            • Pydantic v2 deterministic validation
        </div>
        """,
        unsafe_allow_html=True,
    )


# Automatic first-run on Demo Dataset if not run yet
should_run = run_pipeline or (st.session_state["pipeline_result"] is None and "Live Gmail" not in mode)

if should_run:
    with st.spinner("Ingesting and processing financial telemetry..."):
        try:
            loader = None
            if "Live Gmail" in mode:
                oauth_handler = GmailOAuthHandler(client_secrets_file=client_secrets_path)
                service = oauth_handler.get_gmail_service()
                if not service:
                    st.warning("⚠️ Please click '🔑 Connect Google Account' in the sidebar to authenticate before running.")
                else:
                    loader = LiveGmailLoader(service=service, query=gmail_query, max_results=max_emails)
            else:
                loader = DemoDatasetLoader()

            if loader is not None:
                raw_emails = loader.load_emails()
                st.session_state["emails_by_id"] = {e.message_id: e for e in raw_emails}

                # Run Hybrid Extraction Engine
                engine = HybridExtractionEngine(gemini_api_key=gemini_key or None)
                pipeline_result = engine.process_emails(raw_emails)
                st.session_state["pipeline_result"] = pipeline_result
        except Exception as err:
            st.error(f"Pipeline error: {err}")


# Retrieve current results
result = st.session_state["pipeline_result"]

# Header
st.markdown(
    f"""
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <div>
            <h1 style="font-size: 26px; font-weight: 800; color: #f8fafc; margin: 0;">
                Polarisk Gmail Spend Intelligence
            </h1>
            <p style="color: #94a3b8; font-size: 14px; margin: 4px 0 0 0;">
                Deterministic financial telemetry extraction and statistical anomaly detection
            </p>
        </div>
        <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; border-radius: 9999px; padding: 4px 14px; color: #34d399; font-size: 12px; font-weight: 600;">
            ● {mode.split(':')[0]} Active
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Email Traceability Drawer (if active)
active_trace_id = st.session_state.get("active_trace_msg_id")
if active_trace_id and active_trace_id in st.session_state["emails_by_id"]:
    render_traceability_view(st.session_state["emails_by_id"][active_trace_id])

if result is None or len(result.transactions) == 0:
    render_empty_state()
else:
    # Deterministic Analytics
    summary = SpendMetricsCalculator.compute_summary(result.transactions)
    subscriptions = CadenceDetector.detect_subscriptions(result.transactions)
    anomaly_detector = AnomalyDetector()
    anomalies = anomaly_detector.detect_anomalies(result.transactions)
    explainer = AnomalyExplainer(api_key=gemini_key or None)

    # Top KPI Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_kpi_card(
            title="Net Spend (INR)",
            value=f"₹{summary.total_spend:,.2f}",
            subtitle=f"{summary.total_transactions} verified transactions",
            badge="Audited",
        )
    with col2:
        top_cat = max(summary.category_totals.items(), key=lambda x: x[1])[0] if summary.category_totals else "N/A"
        render_kpi_card(
            title="Top Spend Category",
            value=top_cat,
            subtitle=f"₹{summary.category_totals.get(top_cat, 0):,.2f} allocated",
        )
    with col3:
        render_kpi_card(
            title="Recurring Subscriptions",
            value=str(len(subscriptions)),
            subtitle=f"Run-rate: ₹{sum(s.amount for s in subscriptions):,.2f}/mo",
        )
    with col4:
        high_severity_count = sum(1 for a in anomalies if a.severity == "high")
        render_kpi_card(
            title="Attention Alerts",
            value=str(len(anomalies)),
            subtitle=f"{high_severity_count} high severity anomalies",
            badge="Action Needed" if anomalies else "Clear",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Anomaly & Price Hike Alerts Center
    if anomalies:
        st.markdown("### ⚠️ **Attention Required: Anomaly & Price Spike Alerts**")
        st.caption("Statistical anomalies flagged mathematically with evidence-grounded natural language context.")
        for idx, alert in enumerate(anomalies):
            # Generate explanation if not already generated
            enhanced_explanation = explainer.explain(alert)
            alert.explanation = enhanced_explanation
            render_anomaly_card(alert, key_prefix=f"anomaly_{idx}")

        st.markdown("<br>", unsafe_allow_html=True)

    # Visual Intelligence Tabs
    st.markdown("### 📊 **Spend Telemetry Visualizations**")
    col_chart_left, col_chart_right = st.columns([1.2, 1])

    with col_chart_left:
        trends_df = SpendMetricsCalculator.compute_monthly_trends(result.transactions)
        st.plotly_chart(create_monthly_trend_chart(trends_df), use_container_width=True)

    with col_chart_right:
        st.plotly_chart(create_category_donut_chart(summary.category_totals), use_container_width=True)

    # Top Merchants Chart
    st.plotly_chart(create_top_merchants_chart(summary.merchant_totals, n=7), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Recurring Subscriptions Monitor
    st.markdown("### 🔄 **Active Subscriptions & Recurring Cadence**")
    if subscriptions:
        sub_rows = []
        for s in subscriptions:
            sub_rows.append({
                "Merchant": s.merchant,
                "Amount": f"₹{s.amount:,.2f}",
                "Cadence": s.cadence.capitalize(),
                "Last Billed": s.last_billed_date.strftime("%d %b %Y"),
                "Estimated Next Renewal": s.next_estimated_date.strftime("%d %b %Y") if s.next_estimated_date else "N/A",
                "Category": s.category,
                "Source ID": s.source_message_id,
            })
        st.dataframe(pd.DataFrame(sub_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No recurring subscription patterns detected.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Verified Transactions Ledger
    st.markdown("### 📑 **Verified Financial Transactions Ledger**")
    st.caption("Pydantic v2 validated transactions with confidence score >= 0.85 and cryptographic deduplication.")

    # Search and Filter
    col_filter_search, col_filter_cat, col_filter_type = st.columns([2, 1, 1])
    with col_filter_search:
        search_query = st.text_input("🔍 Search merchant or subject:", placeholder="e.g. Amazon, Netflix, Biryani...")
    with col_filter_cat:
        available_categories = ["All"] + sorted(list(summary.category_totals.keys()))
        selected_cat = st.selectbox("Category Filter:", options=available_categories)
    with col_filter_type:
        selected_type = st.selectbox("Transaction Type:", options=["All", "purchase", "subscription", "bill", "refund"])

    # Filter transactions
    filtered_txns = result.transactions
    if search_query:
        q = search_query.lower()
        filtered_txns = [t for t in filtered_txns if q in t.merchant.lower() or q in t.source_subject.lower()]
    if selected_cat != "All":
        filtered_txns = [t for t in filtered_txns if t.category == selected_cat]
    if selected_type != "All":
        filtered_txns = [t for t in filtered_txns if t.transaction_type == selected_type]

    if filtered_txns:
        txn_rows = []
        for t in filtered_txns:
            txn_rows.append({
                "Date": t.date.strftime("%Y-%m-%d"),
                "Merchant": t.merchant,
                "Amount": f"₹{t.amount:,.2f}",
                "Type": t.transaction_type.capitalize(),
                "Category": t.category,
                "Confidence": f"{t.confidence * 100:.0f}%",
                "Subject Line": t.source_subject,
                "Message ID": t.source_message_id,
            })
        st.dataframe(pd.DataFrame(txn_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No transactions match the specified filter criteria.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Pipeline Audit & Quality Health Accordion
    with st.expander("🛠️ **Pipeline Audit & Ingestion Quality Metrics**", expanded=False):
        col_aud_1, col_aud_2, col_aud_3, col_aud_4 = st.columns(4)
        col_aud_1.metric("Emails Ingested", len(st.session_state["emails_by_id"]))
        col_aud_2.metric("Discarded Noise", len(result.filtered_out_noise))
        col_aud_3.metric("Duplicates Suppressed", len(result.duplicates_detected))
        col_aud_4.metric("Missing Amounts Rejected", len(result.rejected_extractions))

        if result.duplicates_detected:
            st.markdown("##### 🔁 **Suppressed Duplicate Records Audit**")
            st.dataframe(pd.DataFrame(result.duplicates_detected), use_container_width=True, hide_index=True)

        if result.rejected_extractions:
            st.markdown("##### 🚫 **Rejected Unverified Emails Audit**")
            st.dataframe(pd.DataFrame(result.rejected_extractions), use_container_width=True, hide_index=True)

        if result.filtered_out_noise:
            st.markdown("##### 🗑️ **Pre-Filtered Non-Financial Emails**")
            noise_summary = [{"Sender": e.sender, "Subject": e.subject} for e in result.filtered_out_noise]
            st.dataframe(pd.DataFrame(noise_summary), use_container_width=True, hide_index=True)
