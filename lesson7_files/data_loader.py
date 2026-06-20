"""Data loading, cleaning, and transformation utilities for e-commerce analysis.

This module centralises all I/O and data-preparation logic so that the
analysis notebook can stay focused on business questions. The main entry
point is :class:`EcommerceData`, which loads the raw CSV files, builds a
single enriched item-level sales table, and exposes configurable period
filtering so the same analysis can be run for any month/year range.

Typical usage
-------------
>>> data = EcommerceData("ecommerce_data").load()
>>> sales_2023 = data.filter_sales(year=2023)          # full year 2023
>>> sales_q1 = data.filter_sales(year=2023, months=[1, 2, 3])
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

# Order statuses that represent realised, fulfilled revenue.
DELIVERED_STATUS = "delivered"

# Raw CSV file names expected inside the data directory.
RAW_FILES = {
    "orders": "orders_dataset.csv",
    "order_items": "order_items_dataset.csv",
    "products": "products_dataset.csv",
    "customers": "customers_dataset.csv",
    "reviews": "order_reviews_dataset.csv",
    "payments": "order_payments_dataset.csv",
}


def _to_datetime(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Return ``df`` with the given timestamp columns parsed to datetime."""
    df = df.copy()
    for column in columns:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], errors="coerce")
    return df


@dataclass
class EcommerceData:
    """Load and prepare the e-commerce datasets.

    Parameters
    ----------
    data_dir:
        Directory containing the raw ``*_dataset.csv`` files.

    Attributes
    ----------
    raw:
        Dictionary of raw DataFrames keyed by the names in :data:`RAW_FILES`.
    sales:
        Enriched item-level table of delivered orders. One row per order
        item, carrying order, product, customer, and review attributes plus
        derived ``year``, ``month``, and ``delivery_days`` columns.
    """

    data_dir: str
    raw: dict[str, pd.DataFrame] = field(default_factory=dict)
    sales: Optional[pd.DataFrame] = None

    def load(self) -> "EcommerceData":
        """Load raw CSVs and build the enriched sales table.

        Returns ``self`` so calls can be chained.
        """
        self.raw = self._load_raw()
        self.sales = self._build_sales_table()
        return self

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _load_raw(self) -> dict[str, pd.DataFrame]:
        """Read every raw CSV file into a DataFrame."""
        base = Path(self.data_dir)
        raw: dict[str, pd.DataFrame] = {}
        for name, filename in RAW_FILES.items():
            raw[name] = pd.read_csv(base / filename)
        return raw

    # ------------------------------------------------------------------
    # Transformation
    # ------------------------------------------------------------------
    def _build_sales_table(self) -> pd.DataFrame:
        """Build the enriched, delivered, item-level sales table.

        Steps
        -----
        1. Join order items with their parent orders.
        2. Keep only delivered orders (realised revenue).
        3. Parse purchase and delivery timestamps.
        4. Derive ``year``, ``month``, and ``delivery_days``.
        5. Attach product category, customer state, and review score.
        """
        orders = _to_datetime(
            self.raw["orders"],
            ["order_purchase_timestamp", "order_delivered_customer_date"],
        )
        order_items = self.raw["order_items"]

        sales = order_items[
            ["order_id", "order_item_id", "product_id", "price"]
        ].merge(
            orders[
                [
                    "order_id",
                    "customer_id",
                    "order_status",
                    "order_purchase_timestamp",
                    "order_delivered_customer_date",
                ]
            ],
            on="order_id",
            how="inner",
        )

        sales = sales[sales["order_status"] == DELIVERED_STATUS].copy()

        sales["year"] = sales["order_purchase_timestamp"].dt.year
        sales["month"] = sales["order_purchase_timestamp"].dt.month
        sales["delivery_days"] = (
            sales["order_delivered_customer_date"]
            - sales["order_purchase_timestamp"]
        ).dt.days

        # Attach product category (one category per product).
        products = self.raw["products"][["product_id", "product_category_name"]]
        sales = sales.merge(products, on="product_id", how="left")

        # Attach customer state via the customer dimension.
        customers = self.raw["customers"][["customer_id", "customer_state"]]
        sales = sales.merge(customers, on="customer_id", how="left")

        # Attach review score (one score per order). Left join keeps every
        # delivered item; review-based metrics filter to scored rows.
        reviews = self.raw["reviews"][["order_id", "review_score"]]
        sales = sales.merge(reviews, on="order_id", how="left")

        return sales

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    def filter_sales(
        self,
        year: Optional[int] = None,
        months: Optional[Iterable[int]] = None,
    ) -> pd.DataFrame:
        """Return the sales table filtered to a configurable period.

        Parameters
        ----------
        year:
            Calendar year to keep. ``None`` keeps all years.
        months:
            Iterable of month numbers (1-12) to keep. ``None`` keeps all
            months, i.e. the full year.

        Returns
        -------
        pandas.DataFrame
            A copy of the enriched sales table restricted to the period.
        """
        if self.sales is None:
            raise RuntimeError("Call load() before filtering.")
        return filter_by_period(self.sales, year=year, months=months)

    def orders_with_dates(self) -> pd.DataFrame:
        """Return the raw orders table with ``year``/``month`` columns added.

        Useful for order-status analysis, which considers all statuses
        rather than only delivered orders.
        """
        orders = _to_datetime(self.raw["orders"], ["order_purchase_timestamp"])
        orders = orders.copy()
        orders["year"] = orders["order_purchase_timestamp"].dt.year
        orders["month"] = orders["order_purchase_timestamp"].dt.month
        return orders


def filter_by_period(
    df: pd.DataFrame,
    year: Optional[int] = None,
    months: Optional[Iterable[int]] = None,
    year_col: str = "year",
    month_col: str = "month",
) -> pd.DataFrame:
    """Filter a DataFrame to a year and/or set of months.

    Parameters
    ----------
    df:
        Input DataFrame containing ``year_col`` and ``month_col``.
    year:
        Year to keep, or ``None`` for all years.
    months:
        Iterable of months (1-12) to keep, or ``None`` for all months.
    year_col, month_col:
        Names of the year and month columns.

    Returns
    -------
    pandas.DataFrame
        Filtered copy of the input.
    """
    mask = pd.Series(True, index=df.index)
    if year is not None:
        mask &= df[year_col] == year
    if months is not None:
        mask &= df[month_col].isin(list(months))
    return df[mask].copy()
