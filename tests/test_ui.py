"""Unit tests for UI charts and component rendering."""

import pandas as pd
import pytest

from src.ui.charts import (
    create_category_donut_chart,
    create_monthly_trend_chart,
    create_top_merchants_chart,
)


class TestUICharts:
    def test_monthly_trend_chart_with_data(self):
        df = pd.DataFrame([
            {"month": "2026-07", "amount": 5499.00, "transaction_count": 1},
            {"month": "2026-08", "amount": 5499.00, "transaction_count": 1},
            {"month": "2026-09", "amount": 6899.00, "transaction_count": 1},
        ])
        fig = create_monthly_trend_chart(df)
        assert fig is not None
        assert len(fig.data) >= 1

    def test_monthly_trend_chart_empty(self):
        fig = create_monthly_trend_chart(pd.DataFrame())
        assert fig is not None

    def test_category_donut_chart(self):
        cat_data = {"Shopping": 4398.0, "Food": 620.0, "Subscriptions": 649.0}
        fig = create_category_donut_chart(cat_data)
        assert fig is not None
        assert len(fig.data) == 1

    def test_category_donut_chart_empty(self):
        fig = create_category_donut_chart({})
        assert fig is not None

    def test_top_merchants_chart(self):
        merchants = {"Apex Cloud": 35000.0, "Adobe": 6899.0, "Amazon": 3498.0}
        fig = create_top_merchants_chart(merchants)
        assert fig is not None
        assert len(fig.data) == 1

    def test_top_merchants_chart_empty(self):
        fig = create_top_merchants_chart({})
        assert fig is not None
