"""Reusable UI components for Polarisk Streamlit fintech dashboard."""

from __future__ import annotations

from typing import Optional
import streamlit as st

from src.schemas import AnomalyAlert, EmailMessage


def render_kpi_card(title: str, value: str, subtitle: str = "", badge: Optional[str] = None) -> None:
    """Render a modern dark-mode fintech KPI metric card."""
    badge_html = f'<span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; font-size: 11px; padding: 2px 8px; border-radius: 9999px; margin-left: 8px;">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div style="background: #1e293b; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);">
            <div style="color: #94a3b8; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; display: flex; align-items: center;">
                {title} {badge_html}
            </div>
            <div style="color: #f8fafc; font-size: 28px; font-weight: 700; margin: 8px 0 4px 0; letter-spacing: -0.02em;">
                {value}
            </div>
            <div style="color: #64748b; font-size: 12px;">
                {subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(custom_message: Optional[str] = None) -> None:
    """Explicit, polished empty state when zero financial transactions are detected."""
    msg = custom_message or "No financial transactions were detected in the selected mailbox query."
    st.markdown(
        f"""
        <div style="background: rgba(30, 41, 59, 0.6); border: 2px dashed rgba(255, 255, 255, 0.12); border-radius: 16px; padding: 48px 24px; text-align: center; margin: 32px 0;">
            <div style="font-size: 48px; margin-bottom: 12px;">📬</div>
            <h3 style="color: #f8fafc; font-size: 20px; font-weight: 600; margin-bottom: 8px;">Zero Spending Telemetry Detected</h3>
            <p style="color: #94a3b8; font-size: 14px; max-width: 500px; margin: 0 auto 20px auto; line-height: 1.5;">
                {msg}
            </p>
            <div style="display: inline-block; background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 8px; padding: 10px 18px; color: #93c5fd; font-size: 13px;">
                💡 <b>Evaluator Quick-Start</b>: Switch to <b>"Try with Demo Data (18+ Cases)"</b> in the sidebar to inspect price hikes, subscriptions, and edge cases.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_anomaly_card(alert: AnomalyAlert, key_prefix: str = "alert") -> None:
    """Render an alert card with severity indicators and natural language explanation."""
    severity_colors = {
        "high": ("#ef4444", "rgba(239, 68, 68, 0.15)"),
        "medium": ("#f59e0b", "rgba(245, 158, 11, 0.15)"),
        "low": ("#3b82f6", "rgba(59, 130, 246, 0.15)"),
    }
    color, bg = severity_colors.get(alert.severity, ("#6b7280", "rgba(107, 114, 128, 0.15)"))

    type_labels = {
        "price_increase": "Price Increase Spiked",
        "new_merchant": "First-Time High Spend",
        "upcoming_renewal": "Renewal Due Soon",
        "unusual_amount": "Unusual Transaction",
    }
    type_label = type_labels.get(alert.alert_type, alert.alert_type.replace("_", " ").title())

    col_main, col_btn = st.columns([5, 1.2])
    with col_main:
        st.markdown(
            f"""
            <div style="background: #1e293b; border-left: 4px solid {color}; border-radius: 8px; padding: 14px 18px; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <span style="background: {bg}; color: {color}; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase;">
                        {alert.severity} • {type_label}
                    </span>
                    <span style="color: #cbd5e1; font-weight: 600; font-size: 15px;">
                        {alert.merchant}
                    </span>
                    <span style="color: #94a3b8; font-size: 14px; margin-left: auto;">
                        ₹{alert.amount:,.2f}
                    </span>
                </div>
                <div style="color: #e2e8f0; font-size: 13.5px; line-height: 1.45;">
                    {alert.explanation}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_btn:
        if st.button("🔍 Source Email", key=f"{key_prefix}_{alert.alert_id}", use_container_width=True):
            st.session_state["active_trace_msg_id"] = alert.source_message_id
            st.rerun()


def render_traceability_view(email: EmailMessage) -> None:
    """Audit modal showing exact email headers, origin, and decoded body."""
    st.markdown(
        f"""
        <div style="background: #0f172a; border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px; padding: 20px; margin: 16px 0;">
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px; margin-bottom: 14px;">
                <h4 style="color: #60a5fa; margin: 0; font-size: 16px;">📧 Email Audit Provenance</h4>
                <span style="background: rgba(59, 130, 246, 0.2); color: #93c5fd; font-family: monospace; font-size: 11px; padding: 3px 8px; border-radius: 4px;">
                    ID: {email.message_id}
                </span>
            </div>
            <div style="font-size: 13px; color: #94a3b8; line-height: 1.6; margin-bottom: 14px;">
                <div><b style="color: #cbd5e1;">Subject:</b> {email.subject}</div>
                <div><b style="color: #cbd5e1;">Sender:</b> {email.sender}</div>
                <div><b style="color: #cbd5e1;">Date:</b> {email.date_str}</div>
            </div>
            <div style="background: #1e293b; border-radius: 8px; padding: 14px; color: #e2e8f0; font-family: monospace; font-size: 12px; white-space: pre-wrap; max-height: 250px; overflow-y: auto;">
{email.body_text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("✖ Close Provenance View", key="btn_close_trace"):
        st.session_state["active_trace_msg_id"] = None
        st.rerun()
