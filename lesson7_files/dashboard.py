"""E-Commerce Sales Analytics Dashboard (Streamlit).

A professional, interactive dashboard built on the same analysis modules as
``EDA_Refactored.ipynb`` (:mod:`data_loader` and :mod:`business_metrics`).
A global date-range filter drives every KPI and chart, and headline metrics
are compared against the equivalent prior-year period.

Run with::

    streamlit run dashboard.py
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

import data_loader as dl
import business_metrics as bm

# ----------------------------------------------------------------------
# Configuration and styling
# ----------------------------------------------------------------------
DATA_DIR = "ecommerce_data"

PRIMARY = "#1f4e79"        # deep navy for headline series
POSITIVE = "#1a9850"       # green for favourable trends
NEGATIVE = "#d73027"       # red for unfavourable trends
NEUTRAL = "#888888"        # grey for flat / unavailable trends
BLUE_SCALE = "Blues"

st.set_page_config(
    page_title="E-Commerce Sales Analytics",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    .dash-title { font-size: 2rem; font-weight: 800; color: #1f2d3d;
                  margin: 0; padding-top: 0.4rem; }
    .dash-subtitle { color: #6b7280; font-size: 0.95rem; margin-top: 0.2rem; }
    .card { background: #ffffff; border: 1px solid #e6e8eb; border-radius: 12px;
            padding: 18px 22px; box-shadow: 0 1px 3px rgba(16,24,40,0.06); }
    .kpi-card { min-height: 150px; }
    .stat-card { min-height: 170px; display: flex; flex-direction: column;
                 justify-content: center; }
    .card-label { color: #6b7280; font-size: 0.8rem; font-weight: 700;
                  text-transform: uppercase; letter-spacing: 0.05em; }
    .card-value { font-size: 2.1rem; font-weight: 800; color: #1f2d3d;
                  margin-top: 6px; line-height: 1.1; }
    .card-trend { font-size: 0.92rem; font-weight: 600; margin-top: 10px; }
    .trend-up { color: #1a9850; }
    .trend-down { color: #d73027; }
    .trend-flat { color: #888888; }
    .stars { color: #f5a623; font-size: 1.6rem; letter-spacing: 2px;
             margin-top: 6px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Data loading (cached)
# ----------------------------------------------------------------------
@st.cache_data
def load_sales() -> pd.DataFrame:
    """Load and enrich the sales table once per session."""
    return dl.EcommerceData(DATA_DIR).load().sales


# ----------------------------------------------------------------------
# Formatting helpers
# ----------------------------------------------------------------------
def money(value: float) -> str:
    """Format a currency value for KPI cards (e.g. ``$3.36M``, ``$300K``)."""
    if value is None or pd.isna(value):
        return "n/a"
    magnitude = abs(value)
    if magnitude >= 1e6:
        return f"${value / 1e6:.2f}M"
    if magnitude >= 1e3:
        return f"${value / 1e3:.0f}K"
    return f"${value:,.0f}"


def money_short(value: float) -> str:
    """Compact currency for axes/labels (e.g. ``$2M``, ``$1.5M``, ``$300K``)."""
    if value is None or pd.isna(value):
        return ""
    magnitude = abs(value)
    if magnitude >= 1e6:
        text = f"{value / 1e6:.1f}".rstrip("0").rstrip(".")
        return f"${text}M"
    if magnitude >= 1e3:
        return f"${value / 1e3:.0f}K"
    return f"${value:.0f}"


def trend_markup(pct: float, lower_is_better: bool = False) -> str:
    """Return an HTML span describing a percentage trend.

    Green/red is assigned by whether the change is favourable. For metrics
    where a decrease is good (e.g. delivery time), set ``lower_is_better``.
    Magnitude is always shown to two decimal places.
    """
    if pct is None or pd.isna(pct):
        return '<div class="card-trend trend-flat">n/a vs previous period</div>'
    favourable = (pct < 0) if lower_is_better else (pct > 0)
    if pct == 0:
        css, arrow = "trend-flat", "="
    elif favourable:
        css, arrow = "trend-up", ("▲" if pct > 0 else "▼")
    else:
        css, arrow = "trend-down", ("▲" if pct > 0 else "▼")
    return (
        f'<div class="card-trend {css}">{arrow} {abs(pct):.2f}% '
        f'vs previous period</div>'
    )


def kpi_card(label: str, value: str, trend_html: str = "") -> str:
    """Build the HTML for a KPI card."""
    return (
        f'<div class="card kpi-card">'
        f'<div class="card-label">{label}</div>'
        f'<div class="card-value">{value}</div>'
        f'{trend_html}'
        f'</div>'
    )


def stars_markup(score: float) -> str:
    """Render a 0-5 review score as filled/empty stars."""
    if pd.isna(score):
        return ""
    filled = int(round(score))
    return "★" * filled + "☆" * (5 - filled)


# ----------------------------------------------------------------------
# Chart builders
# ----------------------------------------------------------------------
def currency_axis(fig: go.Figure, axis: str, max_value: float) -> None:
    """Apply compact currency tick labels ($300K / $2M) to an axis."""
    if not max_value or pd.isna(max_value):
        return
    upper = max_value * 1.1
    step = upper / 5
    ticks = [step * i for i in range(6)]
    text = [money_short(t) for t in ticks]
    if axis == "y":
        fig.update_yaxes(tickvals=ticks, ticktext=text)
    else:
        fig.update_xaxes(tickvals=ticks, ticktext=text)


def revenue_trend_chart(current: pd.DataFrame, previous: pd.DataFrame) -> go.Figure:
    """Monthly revenue: solid current period, dashed previous period."""
    cur = bm.revenue_time_series(current, "M")
    prev = bm.revenue_time_series(previous, "M")

    # Align the previous period onto the current months (shift forward 1 year).
    prev_aligned = prev.copy()
    prev_aligned.index = prev_aligned.index + 12
    prev_aligned = prev_aligned.reindex(cur.index)

    labels = [p.strftime("%b %Y") for p in cur.index]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=labels, y=cur.values, mode="lines+markers", name="Current period",
            line=dict(color=PRIMARY, width=3),
        )
    )
    if prev_aligned.notna().any():
        fig.add_trace(
            go.Scatter(
                x=labels, y=prev_aligned.values, mode="lines+markers",
                name="Previous period",
                line=dict(color=NEUTRAL, width=2, dash="dash"),
            )
        )
    fig.update_layout(
        title="Revenue Trend",
        xaxis_title="Month", yaxis_title="Revenue (USD)",
        margin=dict(l=10, r=10, t=50, b=10), height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
    )
    fig.update_yaxes(showgrid=True, gridcolor="#eceff3")
    fig.update_xaxes(showgrid=True, gridcolor="#eceff3")
    max_val = max(cur.max(), prev_aligned.max() if prev_aligned.notna().any() else 0)
    currency_axis(fig, "y", max_val)
    return fig


def category_chart(current: pd.DataFrame) -> go.Figure:
    """Top 10 product categories by revenue, blue gradient, descending."""
    top = bm.revenue_by_category(current).head(10)
    # Horizontal bar: plot ascending so the largest sits on top.
    top = top.iloc[::-1]
    fig = go.Figure(
        go.Bar(
            x=top.values, y=top.index, orientation="h",
            marker=dict(color=top.values, colorscale=BLUE_SCALE),
            text=[money_short(v) for v in top.values],
            textposition="outside", cliponaxis=False,
        )
    )
    fig.update_layout(
        title="Top 10 Categories by Revenue",
        xaxis_title="Revenue (USD)", yaxis_title="",
        margin=dict(l=10, r=10, t=50, b=10), height=360,
    )
    currency_axis(fig, "x", top.max())
    return fig


def state_chart(current: pd.DataFrame) -> go.Figure:
    """US choropleth of revenue by customer state, blue gradient."""
    state_revenue = bm.revenue_by_state(current)
    fig = px.choropleth(
        state_revenue, locations="customer_state", color="price",
        locationmode="USA-states", scope="usa", color_continuous_scale=BLUE_SCALE,
    )
    fig.update_layout(
        title="Revenue by State",
        margin=dict(l=10, r=10, t=50, b=10), height=360,
        coloraxis_colorbar=dict(title="Revenue", tickprefix="$"),
        geo=dict(bgcolor="rgba(0,0,0,0)", lakecolor="white"),
    )
    return fig


def satisfaction_chart(current: pd.DataFrame) -> go.Figure:
    """Average review score by delivery-time bucket."""
    speed = bm.review_score_by_delivery_speed(current)
    fig = go.Figure(
        go.Bar(
            x=speed["delivery_time"].astype(str), y=speed["review_score"],
            marker=dict(color=PRIMARY),
            text=[f"{v:.2f}" for v in speed["review_score"]],
            textposition="outside", cliponaxis=False,
        )
    )
    fig.update_layout(
        title="Satisfaction vs Delivery Time",
        xaxis_title="Delivery time", yaxis_title="Average review score (1-5)",
        margin=dict(l=10, r=10, t=50, b=10), height=360,
        yaxis=dict(range=[0, 5]),
    )
    fig.update_yaxes(showgrid=True, gridcolor="#eceff3")
    return fig


# ----------------------------------------------------------------------
# App
# ----------------------------------------------------------------------
sales = load_sales()
data_min = sales["order_purchase_timestamp"].min().date()
data_max = sales["order_purchase_timestamp"].max().date()

# Default to the full year 2023 (matching the notebook's default analysis).
default_start = max(dt.date(2023, 1, 1), data_min)
default_end = min(dt.date(2023, 12, 31), data_max)

# --- Header: title (left) and global date filter (right) ---
header_left, header_right = st.columns([3, 2])
with header_left:
    st.markdown('<div class="dash-title">E-Commerce Sales Analytics</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="dash-subtitle">Performance overview with '
                'prior-year comparison</div>', unsafe_allow_html=True)
with header_right:
    date_range = st.date_input(
        "Date range", value=(default_start, default_end),
        min_value=data_min, max_value=data_max,
    )

# Normalise the date filter (date_input may return a single date mid-edit).
if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = (
        date_range[0] if isinstance(date_range, (tuple, list)) else date_range
    )

# Current period and equivalent prior-year period.
current = dl.filter_by_date(sales, start_date, end_date)
prev_start = (pd.Timestamp(start_date) - pd.DateOffset(years=1)).date()
prev_end = (pd.Timestamp(end_date) - pd.DateOffset(years=1)).date()
previous = dl.filter_by_date(sales, prev_start, prev_end)

st.caption(
    f"Showing {start_date:%b %d, %Y} to {end_date:%b %d, %Y} "
    f"(compared with {prev_start:%b %d, %Y} to {prev_end:%b %d, %Y})"
)

if current.empty:
    st.warning("No orders fall within the selected date range.")
    st.stop()

# --- KPI row: 4 cards ---
rev_cur, rev_prev = bm.total_revenue(current), bm.total_revenue(previous)
aov_cur, aov_prev = bm.average_order_value(current), bm.average_order_value(previous)
ord_cur, ord_prev = bm.total_orders(current), bm.total_orders(previous)
monthly_growth = bm.mean_monthly_growth(current)

k1, k2, k3, k4 = st.columns(4)
k1.markdown(
    kpi_card("Total Revenue", money(rev_cur),
             trend_markup(bm.growth_rate(rev_cur, rev_prev) * 100)),
    unsafe_allow_html=True,
)
k2.markdown(
    kpi_card("Monthly Growth",
             "n/a" if pd.isna(monthly_growth) else f"{monthly_growth * 100:.2f}%"),
    unsafe_allow_html=True,
)
k3.markdown(
    kpi_card("Average Order Value", money(aov_cur),
             trend_markup(bm.growth_rate(aov_cur, aov_prev) * 100)),
    unsafe_allow_html=True,
)
k4.markdown(
    kpi_card("Total Orders", f"{ord_cur:,}",
             trend_markup(bm.growth_rate(ord_cur, ord_prev) * 100)),
    unsafe_allow_html=True,
)

st.write("")

# --- Charts grid: 2x2 ---
row1_left, row1_right = st.columns(2)
with row1_left:
    st.plotly_chart(revenue_trend_chart(current, previous), width="stretch")
with row1_right:
    st.plotly_chart(category_chart(current), width="stretch")

row2_left, row2_right = st.columns(2)
with row2_left:
    st.plotly_chart(state_chart(current), width="stretch")
with row2_right:
    st.plotly_chart(satisfaction_chart(current), width="stretch")

st.write("")

# --- Bottom row: 2 cards ---
del_cur = bm.average_delivery_time(current)
del_prev = bm.average_delivery_time(previous)
review = bm.average_review_score(current)

b1, b2 = st.columns(2)
delivery_trend = trend_markup(
    bm.growth_rate(del_cur, del_prev) * 100, lower_is_better=True
)
b1.markdown(
    f'<div class="card stat-card">'
    f'<div class="card-label">Average Delivery Time</div>'
    f'<div class="card-value">{del_cur:.2f} days</div>'
    f'{delivery_trend}'
    f'</div>',
    unsafe_allow_html=True,
)
b2.markdown(
    f'<div class="card stat-card">'
    f'<div class="card-label">Review Score</div>'
    f'<div class="card-value">{review:.2f}</div>'
    f'<div class="stars">{stars_markup(review)}</div>'
    f'<div class="card-label" style="margin-top:8px;">Average Review Score</div>'
    f'</div>',
    unsafe_allow_html=True,
)
