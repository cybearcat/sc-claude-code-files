# E-Commerce Sales Analysis

Refactored exploratory data analysis of e-commerce performance. The analysis
measures revenue, product, geographic, and customer-experience metrics for a
configurable period (default: full-year 2023 compared with 2022).

## Project structure

| File | Purpose |
| --- | --- |
| `EDA_Refactored.ipynb` | Narrative analysis notebook with documentation and charts |
| `data_loader.py` | Loads, cleans, merges, and period-filters the raw data |
| `business_metrics.py` | Pure metric calculations (revenue, products, geography, experience) |
| `requirements.txt` | Python dependencies |
| `ecommerce_data/` | Raw `*_dataset.csv` source files |

The notebook stays focused on business questions: all data preparation lives
in `data_loader.py` and all metric logic lives in `business_metrics.py`.

## Setup

```bash
pip install -r requirements.txt
```

## Running the analysis

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
