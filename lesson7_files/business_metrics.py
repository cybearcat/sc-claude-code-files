"""Business metric calculations for e-commerce sales analysis.

Every function in this module is a pure calculation: it takes one or more
already-prepared DataFrames (see :mod:`data_loader`) and returns a number,
Series, or small DataFrame. No file I/O, filtering by period, or plotting
happens here, which keeps the metrics reusable across any date range or
dataset that follows the same schema.

Revenue convention
------------------
Revenue is the sum of item ``price`` over delivered order items. Freight is
excluded, and items are not de-duplicated to the order level, matching the
original analysis.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

# Column names used across the metrics.
PRICE_COL = "price"
ORDER_COL = "order_id"
MONTH_COL = "month"
CATEGORY_COL = "product_category_name"
STATE_COL = "customer_state"
REVIEW_COL = "review_score"
DELIVERY_COL = "delivery_days"


# ----------------------------------------------------------------------
# Revenue and order metrics
# ----------------------------------------------------------------------
def total_revenue(df: pd.DataFrame) -> float:
    """Total revenue: sum of item prices over the supplied sales rows."""
    return float(df[PRICE_COL].sum())


def total_orders(df: pd.DataFrame) -> int:
    """Number of distinct orders in the supplied sales rows."""
    return int(df[ORDER_COL].nunique())


def average_order_value(df: pd.DataFrame) -> float:
    """Average revenue per order (order-total price averaged across orders)."""
    return float(df.groupby(ORDER_COL)[PRICE_COL].sum().mean())


def growth_rate(current: float, previous: float) -> float:
    """Fractional change from ``previous`` to ``current``.

    Returns ``(current - previous) / previous``. Multiply by 100 for a
    percentage. ``previous`` of zero yields ``nan``.
    """
    if previous == 0:
        return float("nan")
    return (current - previous) / previous


# ----------------------------------------------------------------------
# Time-series metrics
# ----------------------------------------------------------------------
def monthly_revenue(df: pd.DataFrame) -> pd.Series:
    """Revenue summed by month, indexed by month number (1-12)."""
    return df.groupby(MONTH_COL)[PRICE_COL].sum()


def monthly_growth(df: pd.DataFrame) -> pd.Series:
    """Month-over-month fractional revenue change.

    The first month is ``NaN`` because it has no prior month.
    """
    return monthly_revenue(df).pct_change()


def mean_monthly_growth(df: pd.DataFrame) -> float:
    """Average of the month-over-month growth rates.

    Mirrors the original metric (mean of ``pct_change`` values).
    """
    return float(monthly_growth(df).mean())


# ----------------------------------------------------------------------
# Product and geographic metrics
# ----------------------------------------------------------------------
def revenue_by_category(df: pd.DataFrame) -> pd.Series:
    """Revenue by product category, sorted descending."""
    return (
        df.groupby(CATEGORY_COL)[PRICE_COL]
        .sum()
        .sort_values(ascending=False)
    )


def revenue_by_state(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue by customer state, sorted descending.

    Returned as a two-column DataFrame (``customer_state``, ``price``) ready
    for a choropleth map.
    """
    return (
        df.groupby(STATE_COL)[PRICE_COL]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )


# ----------------------------------------------------------------------
# Customer-experience metrics
# ----------------------------------------------------------------------
def _scored_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Unique scored orders with their delivery time and review score.

    Keeps only rows that carry a review score, then de-duplicates to one row
    per (order, delivery time, score) so order-level metrics are not weighted
    by the number of items in an order.
    """
    scored = df[df[REVIEW_COL].notna()]
    return scored[[ORDER_COL, DELIVERY_COL, REVIEW_COL]].drop_duplicates()


def average_review_score(df: pd.DataFrame) -> float:
    """Average review score across scored orders."""
    return float(_scored_orders(df)[REVIEW_COL].mean())


def review_score_distribution(df: pd.DataFrame) -> pd.Series:
    """Share of scored orders at each review score (1-5), indexed by score."""
    return (
        _scored_orders(df)[REVIEW_COL]
        .value_counts(normalize=True)
        .sort_index()
    )


def average_delivery_time(df: pd.DataFrame) -> float:
    """Average delivery time in days across scored orders."""
    return float(_scored_orders(df)[DELIVERY_COL].mean())


def categorize_delivery_speed(days: float) -> str:
    """Bucket a delivery time (days) into the original speed categories.

    Buckets: ``1-3 days``, ``4-7 days``, ``8+ days``.
    """
    if days <= 3:
        return "1-3 days"
    if days <= 7:
        return "4-7 days"
    return "8+ days"


def review_score_by_delivery_day(df: pd.DataFrame) -> pd.DataFrame:
    """Average review score for each exact delivery time in days.

    Returns a DataFrame with columns ``delivery_days`` and ``review_score``,
    ordered by delivery time.
    """
    scored = _scored_orders(df)
    return (
        scored.groupby(DELIVERY_COL)[REVIEW_COL].mean().reset_index()
    )


def review_score_by_delivery_speed(df: pd.DataFrame) -> pd.DataFrame:
    """Average review score per delivery-speed bucket.

    Returns a DataFrame with columns ``delivery_time`` and ``review_score``,
    ordered from fastest to slowest.
    """
    scored = _scored_orders(df).copy()
    scored["delivery_time"] = scored[DELIVERY_COL].apply(categorize_delivery_speed)
    result = (
        scored.groupby("delivery_time")[REVIEW_COL].mean().reset_index()
    )
    order = ["1-3 days", "4-7 days", "8+ days"]
    result["delivery_time"] = pd.Categorical(
        result["delivery_time"], categories=order, ordered=True
    )
    return result.sort_values("delivery_time").reset_index(drop=True)


# ----------------------------------------------------------------------
# Order-status metric (operates on the full orders table, not just sales)
# ----------------------------------------------------------------------
def order_status_distribution(orders_df: pd.DataFrame) -> pd.Series:
    """Share of orders in each status for the supplied (period-filtered) orders."""
    return orders_df["order_status"].value_counts(normalize=True)


# ----------------------------------------------------------------------
# Convenience: period summary
# ----------------------------------------------------------------------
def period_summary(
    df: pd.DataFrame, comparison: Optional[pd.DataFrame] = None
) -> dict:
    """Bundle the headline metrics for a period into a dictionary.

    Parameters
    ----------
    df:
        Sales rows for the focus period.
    comparison:
        Optional sales rows for a comparison period (e.g. prior year). When
        supplied, year-over-year growth rates are included.
    """
    summary = {
        "total_revenue": total_revenue(df),
        "total_orders": total_orders(df),
        "average_order_value": average_order_value(df),
        "mean_monthly_growth": mean_monthly_growth(df),
        "average_review_score": average_review_score(df),
        "average_delivery_time": average_delivery_time(df),
    }
    if comparison is not None:
        summary["revenue_growth"] = growth_rate(
            summary["total_revenue"], total_revenue(comparison)
        )
        summary["orders_growth"] = growth_rate(
            summary["total_orders"], total_orders(comparison)
        )
        summary["aov_growth"] = growth_rate(
            summary["average_order_value"], average_order_value(comparison)
        )
    return summary
