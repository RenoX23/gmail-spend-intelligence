"""Interactive Plotly charts styled for modern dark-mode fintech dashboards."""

from __future__ import annotations

from typing import Dict
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


FINTECH_DARK_LAYOUT = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"color": "#e0e6ed", "family": "Inter, -apple-system, sans-serif"},
    "margin": {"l": 20, "r": 20, "t": 40, "b": 20},
}


def create_monthly_trend_chart(df_trends: pd.DataFrame) -> go.Figure:
    """Monthly spend trend line and bar hybrid chart."""
    if df_trends.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No trend data available",
            showarrow=False,
            font={"size": 16, "color": "#8892b0"},
        )
        fig.update_layout(**FINTECH_DARK_LAYOUT)
        return fig

    fig = go.Figure()

    # Bar chart for monthly volume
    fig.add_trace(
        go.Bar(
            x=df_trends["month"],
            y=df_trends["amount"],
            name="Monthly Spend",
            marker_color="#3b82f6",
            opacity=0.8,
            hovertemplate="<b>%{x}</b><br>Spend: ₹%{y:,.2f}<extra></extra>",
        )
    )

    # Line chart trend overlay
    fig.add_trace(
        go.Scatter(
            x=df_trends["month"],
            y=df_trends["amount"],
            name="Trend Line",
            mode="lines+markers",
            line={"color": "#10b981", "width": 3, "shape": "spline"},
            marker={"size": 8, "color": "#10b981"},
            hovertemplate="<b>%{x}</b><br>₹%{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        **FINTECH_DARK_LAYOUT,
        title={"text": "Monthly Spending Velocity (INR)", "font": {"size": 16, "color": "#f8fafc"}},
        xaxis={"gridcolor": "rgba(255,255,255,0.08)", "tickfont": {"color": "#94a3b8"}},
        yaxis={"gridcolor": "rgba(255,255,255,0.08)", "tickfont": {"color": "#94a3b8"}, "tickprefix": "₹"},
        showlegend=False,
        height=320,
    )
    return fig


def create_category_donut_chart(category_totals: Dict[str, float]) -> go.Figure:
    """Category breakdown donut chart."""
    if not category_totals or sum(category_totals.values()) <= 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No category data available",
            showarrow=False,
            font={"size": 16, "color": "#8892b0"},
        )
        fig.update_layout(**FINTECH_DARK_LAYOUT)
        return fig

    labels = list(category_totals.keys())
    values = list(category_totals.values())

    colors = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#64748b"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker={"colors": colors[: len(labels)], "line": {"color": "#0f172a", "width": 2}},
                textinfo="percent+label",
                textposition="outside",
                hovertemplate="<b>%{label}</b><br>Total: ₹%{value:,.2f}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        **FINTECH_DARK_LAYOUT,
        title={"text": "Spend by Category", "font": {"size": 16, "color": "#f8fafc"}},
        showlegend=False,
        height=320,
    )
    return fig


def create_top_merchants_chart(merchant_totals: Dict[str, float], n: int = 6) -> go.Figure:
    """Horizontal bar chart of top merchants by spend volume."""
    if not merchant_totals:
        fig = go.Figure()
        fig.add_annotation(
            text="No merchant data available",
            showarrow=False,
            font={"size": 16, "color": "#8892b0"},
        )
        fig.update_layout(**FINTECH_DARK_LAYOUT)
        return fig

    sorted_items = sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:n]
    merchants = [item[0] for item in reversed(sorted_items)]
    amounts = [item[1] for item in reversed(sorted_items)]

    fig = go.Figure(
        go.Bar(
            x=amounts,
            y=merchants,
            orientation="h",
            marker={"color": "#6366f1", "line": {"color": "#818cf8", "width": 1}},
            hovertemplate="<b>%{y}</b><br>Total: ₹%{x:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        **FINTECH_DARK_LAYOUT,
        title={"text": f"Top {len(sorted_items)} Merchants by Spend", "font": {"size": 16, "color": "#f8fafc"}},
        xaxis={"gridcolor": "rgba(255,255,255,0.08)", "tickprefix": "₹", "tickfont": {"color": "#94a3b8"}},
        yaxis={"gridcolor": "rgba(0,0,0,0)", "tickfont": {"color": "#cbd5e1"}},
        height=320,
    )
    return fig
