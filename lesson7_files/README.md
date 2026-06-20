# E-Commerce Sales Analysis

Refactored exploratory data analysis of e-commerce performance, available as
both a narrative notebook and an interactive Streamlit dashboard. The analysis
measures revenue, product, geographic, and customer-experience metrics for a
configurable period (default: full-year 2023 compared with 2022).

## Project structure

| File | Purpose |
| --- | --- |
| `dashboard.py` | Interactive Streamlit dashboard (KPIs, charts, date filter) |
| `EDA_Refactored.ipynb` | Narrative analysis notebook with documentation and charts |
| `data_loader.py` | Loads, cleans, merges, and period-filters the raw data |
| `business_metrics.py` | Pure metric calculations (revenue, products, geography, experience) |
| `requirements.txt` | Python dependencies |
| `ecommerce_data/` | Raw `*_dataset.csv` source files |

Both the notebook and the dashboard stay focused on business questions: all
data preparation lives in `data_loader.py` and all metric logic lives in
`business_metrics.py`.

## Setup

```bash
pip install -r requirements.txt
```

## Running the dashboard

Launch the interactive dashboard with:

```bash
streamlit run dashboard.py
```

The dashboard opens in your browser and is laid out as:

- **Header:** title on the left, a global date-range filter on the right. The
  filter drives every KPI and chart, and metrics are compared against the
  equivalent prior-year period.
- **KPI row:** Total Revenue, Monthly Growth, Average Order Value, and Total
  Orders. Total Revenue, Average Order Value, and Total Orders carry a trend
  indicator versus the previous period (green for favourable, red for
  unfavourable), shown to two decimal places.
- **Charts (2x2):** monthly revenue trend (solid current vs dashed previous
  period), top 10 categories by revenue (blue gradient), revenue by state (US
  choropleth), and average review score by delivery-time bucket.
- **Bottom row:** average delivery time (with a trend indicator, where faster
  is favourable) and the average review score shown as a large number with
  stars.

All charts are built with Plotly and update live as the date filter changes.

## Running the analysis notebook

Open `EDA_Refactored.ipynb` in Jupyter and run all cells, or execute it
headlessly:

```bash
jupyter nbconvert --to notebook --execute --inplace EDA_Refactored.ipynb
```

## Configuring the period

The analysis is driven by a single configuration cell near the top of the
notebook. Change these values and re-run to analyse any period:

```python
ANALYSIS_YEAR = 2023        # focus year
ANALYSIS_MONTHS = None      # None = full year; e.g. [1, 2, 3] for Q1
COMPARISON_YEAR = 2022      # None to skip year-over-year comparison
DATA_DIR = "ecommerce_data"
```

The period filter is applied to `order_purchase_timestamp`. Every metric,
table, and chart downstream respects the configuration, so no other cell
needs editing.

## Using the modules directly

The modules can be reused outside the notebook for any dataset that follows
the same schema:

```python
import data_loader as dl
import business_metrics as bm

data = dl.EcommerceData("ecommerce_data").load()
sales = data.filter_sales(year=2023, months=[1, 2, 3])   # Q1 2023
prior = data.filter_sales(year=2022, months=[1, 2, 3])   # Q1 2022

print(bm.total_revenue(sales))
print(bm.growth_rate(bm.total_revenue(sales), bm.total_revenue(prior)))
print(bm.revenue_by_category(sales))

# Or get everything at once:
summary = bm.period_summary(sales, comparison=prior)
```

## Metrics computed

- **Revenue:** total revenue, year-over-year growth, month-over-month trend
- **Order economics:** average order value, total orders, year-over-year growth
- **Products:** revenue by product category
- **Geography:** revenue by customer state (choropleth map)
- **Customer experience:** average review score, review-score distribution,
  average delivery time, review score by delivery-speed bucket, and the
  order-status mix

Revenue metrics are based on **delivered** orders only and use item `price`
(freight excluded), so they reflect realised revenue.
