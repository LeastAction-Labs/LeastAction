# Dynamic Reporting with Metric standardization and CICD using PostgreSQL

This example walks through a complete sales analytics pipeline built on PostgreSQL. It demonstrates three ideas that transfer to any reporting use case: generating realistic data at scale, computing a standardized metric library using a dynamic cube, and assembling any report from that library using a template — without writing new SQL for each one.

The full package is available at the [LeastAction Samples repository](https://github.com/LeastAction-Labs/LeastAction-samples) under `DemoSaleReportingTasks_Postgresql`.

---

## What This Pipeline Does

The pipeline has six tasks that run in sequence:

```
00_fact_sales_daily.sql               — Create schema + generate random sales data
        ↓
01_cube_dynamic_transform.sql         — Aggregate across all dimension combinations (CUBE)
        ↓
02_stage2_metrics_dod_rolling.sql     — DOD, WOW, rolling windows, MTD, YTD
        ↓
03_stage3_final_metrics_yoy_lookup.sql — YOY, rankings, penetration metrics
        ↓
sales_performance_reporting.json      ┐  — Generate HTML reports from metric templates
category_performance_reporting.json   ┘
```

Each task waits for its parent to complete before running. The two reporting tasks run in parallel once the metric pipeline finishes.

---

## The Core Idea: Dynamic Cube + Metric Standardization

The key design choice is separating **metric computation** from **report presentation**.

### The metric store

After the transformation stages, every metric lives in a single table (`fact_product_agg_daily`) in a key-value structure:

| date | dim_key_grouping | dim_value | metric_key | metric_value |
|------|-----------------|-----------|-----------|-------------|
| 2026-03-06 | `Laptop Pro 15::dim_category::North America::dim_subregion::dim_store` | `Laptop Pro 15::North America` | `revenue` | 48234.50 |
| 2026-03-06 | `Laptop Pro 15::dim_category::North America::dim_subregion::dim_store` | `Laptop Pro 15::North America` | `revenue_dod` | 1203.20 |
| 2026-03-06 | `Laptop Pro 15::dim_category::North America::dim_subregion::dim_store` | `Laptop Pro 15::North America` | `revenue_yoy_pct` | 12.4 |

The `dim_key_grouping` encodes the aggregation structure. Fixed dimension values appear as literals (`Laptop Pro 15`, `North America`). Rolled-up dimensions appear as `dim_*` placeholders (`dim_category`, `dim_subregion`, `dim_store`). Every combination produced by the CUBE is stored — the reporting layer just selects slices.

### The full metric library

Across the three transformation stages, the pipeline computes:

| Metric suffix | What it measures |
|---------------|-----------------|
| `revenue`, `units_sold`, `cost`, `profit`, `discount` | Base daily totals |
| `_dod` | Day-over-day change |
| `_dod_pct` | Day-over-day % change |
| `_wow` | Week-over-week change |
| `_mtd` | Month-to-date cumulative |
| `_ytd` | Year-to-date cumulative |
| `_avg_10d`, `_sum_10d`, `_min_10d`, `_max_10d` | 10-day rolling window |
| `_std_10d` | 10-day rolling volatility |
| `_yoy`, `_yoy_pct` | Year-over-year change and % |
| `_ly`, `_lw` | Last year / last week lookup |
| `_dodly`, `_dodly_pct` | Today's DOD vs. same day last year |
| `_mtd_yoy`, `_ytd_yoy` | MTD and YTD vs. prior year |
| `_rank` | Daily rank within grouping |
| `_pct_of_total` | Share of group total |

All metrics follow the same structure. Adding a new metric is adding one more `INSERT` block with the same pattern.

### The dynamic cube

PostgreSQL's `CUBE` operator generates every possible combination of aggregation levels across your dimensions. For (product, category, region, sub_region, store), it produces:

- Product + Category + Region + Sub-region (leaf level)
- Product + Category + Region (sub-region rolled up)
- Product + Category (region + sub-region rolled up)
- Category only, Region only, Grand total
- ... every other combination

Instead of writing a separate query for each rollup, the CUBE produces all of them at once. The `dim_cube_config` table controls which dimensions are active and the `dim_cube_filter_rules` table prevents nonsensical combinations (e.g., sub-region without a region).

### Report templates — with dynamic row expansion

Each report is a JSON file that selects specific slices from the metric store. No SQL in the report definition. Each entry in the `metric_template` array defines one section of the report:

```json
{
  "display_name": "Laptop Pro 15 - Revenue by Region",
  "dim_key_grouping": "Laptop Pro 15::dim_category::*::dim_subregion::dim_store",
  "metric_key": "revenue",
  "cell_format": "${value:,.2f}",
  "cell_bg_color": "#E8F5E9",
  "cell_text_color": "#2E7D32",
  "comment": "Dynamic rows: one per region for Laptop Pro 15"
}
```

The `*` in the `dim_key_grouping` is a **dynamic expansion marker**. It means: match any real dimension value at this position (not a `dim_*` placeholder), and produce one row per distinct value found. The example above produces one row per region that has data for Laptop Pro 15 — automatically, with no template changes needed when regions are added or removed.

Fixed tokens (`Laptop Pro 15`, `dim_category`, `dim_subregion`, `dim_store`) are matched exactly, ensuring the right aggregation level is returned and no cross-granularity bleed occurs.

For a single-value row (no expansion), leave `dim_key_grouping` as a fully literal string. For the grand total, set it to `null`.

#### Template modes at a glance

| `dim_key_grouping` | Behaviour |
|--------------------|-----------|
| `"Laptop Pro 15::dim_category::*::dim_subregion::dim_store"` | Dynamic: one row per distinct region value |
| `"dim_product::dim_category::North America::dim_subregion::dim_store"` | Single row: North America total, all products |
| `null` | Single row: grand total across everything |

To add a new report, create a new JSON file with a different `metric_template`. The SQL pipeline does not change.

---

## Sample Report

![Alt text](/docs/examples/postgres_sales_reporting/Category%20&%20Channel%20Performance.png "Optional Title")

---

## What You Need

### A PostgreSQL database

Any PostgreSQL instance accessible from your LeastAction environment. The pipeline creates all tables and procedures — nothing to pre-configure in the database beyond having a schema to write to.

### The `PostgresqlExecuteSQL` operator

Used by the four SQL transformation tasks. Executes the SQL payload against your PostgreSQL database. Available in the LeastAction community catalog.

### The `PostgresqlGenerateHtmlTableReport` operator

Used by the two reporting tasks. Reads from `fact_product_agg_daily`, applies the metric template, generates a styled HTML report, saves it to a PostgreSQL output table, and registers it as an `html_report` asset in the LeastAction catalog.

### A PostgreSQL connection

A connection in your LeastAction catalog with the following fields:

```json
{
  "host": "your-postgres-host",
  "port": 5432,
  "database": "analytics_db",
  "user": "your_user",
  "password": "your_password"
}
```

Name the connection `postgresql` to match what the task files expect, or update `connection_name` in each task file after importing.

---

## Importing the Pipeline

The pipeline ships as Git-ready task files — SQL files and JSON files, each with LeastAction metadata embedded. Use `LeastActionGitToTask` to import them.

### Step 1 — Set up the Git source

The task files live at:

```
DemoSaleReportingTasks_Postgresql/
├── 00_fact_sales_daily.sql
├── 01_cube_dynamic_transform.sql
├── 02_stage2_metrics_dod_rolling.sql
├── 03_stage3_final_metrics_yoy_lookup.sql
├── sales_performance_reporting.json
├── sales_performance_reporting.json.leastaction.json
├── category_performance_reporting.json
└── category_performance_reporting.json.leastaction.json
```

SQL files carry their metadata in the comment block at the top. JSON payloads (report definitions) carry their metadata in a companion `.leastaction.json` file.

### Step 2 — Create a workflow

Create a new workflow in LeastAction. This is where the six tasks will live.

### Step 3 — Add `LeastActionGitToTask` as a preAction

On the workflow, add `LeastActionGitToTask` as a preAction:

```json
{
  "repo_url": "https://github.com/LeastAction-Labs/LeastAction-samples",
  "branch": "main",
  "sub_path": "DemoSaleReportingTasks_Postgresql",
  "workflow_name": "<your workflow name>"
}
```

### Step 4 — Run the preAction

Trigger the preAction from the workflow. It clones the repository, reads each task file, and creates the six tasks in your workflow. Dependencies are wired automatically from the `pre_actions` metadata in each file.

### Step 5 — Verify the connection

Open each task and confirm the connection is set to your PostgreSQL connection.

### Step 6 — Set the reporting output location

Open `sales_performance_reporting` and `category_performance_reporting`. In the payload, update `output_parent_laui` to the laui of an asset folder in your catalog where the HTML reports should be saved.

---

## Running the Pipeline

### First run — generate data

Trigger the workflow. The first task (`00_fact_sales_daily.sql`) creates the fact table and dimension tables, then calls the stored procedure to generate sales data.

By default it generates **100,000 rows** — enough to see real results quickly. To generate more, edit the procedure call in the SQL before importing:

```sql
-- 100,000 rows (default, fast)
CALL generate_sample_sales_data(p_num_rows := 100000);

-- 10 million rows (realistic scale)
CALL generate_sample_sales_data(
    p_num_rows := 10000000,
    p_start_date := '2023-01-01',
    p_end_date := '2026-12-31'
);
```

The generated data covers:
- **100 products** across 10 product names
- **10 categories** (Electronics, Computers, Accessories, Furniture, and more)
- **20 regions** across 5 global regions (North America, Europe, Asia Pacific, Latin America, Middle East Africa)
- **1,000 customers** in three segments (Premium, Standard, Budget)
- **500 stores** in three types (Flagship, Standard, Outlet)
- **4 sales channels** (Online, In-Store, Phone, Mobile App)

### Subsequent runs

On an hourly schedule (the default `0 * * * *`), the pipeline re-runs the transformation stages and regenerates reports. The fact table is rebuilt by the first task — to append rather than rebuild, edit the SQL before importing.

---

## Viewing the Reports

When the two reporting tasks complete, the HTML reports are saved to the asset folder you configured.

### Finding the reports

Navigate to your asset folder in the LeastAction catalog. You will see two items:

- **Sales Performance Dashboard - Product & Region Analysis** — corporate blue theme
- **Category & Channel Performance - Multi-Metric Dashboard** — modern green theme

Click any report to open the full HTML view.

### What the sales performance report shows

Each `*` in a template entry expands into one row per distinct dimension value. The report is built dynamically — adding a new region to the data means a new row appears in the report automatically on the next run.

| Section | Template mode | What appears |
|---------|--------------|-------------|
| Laptop Pro 15 - Revenue by Region | `*` on region | One row per region with data for Laptop Pro 15 + a Total row |
| Laptop Pro 15 - Revenue DOD | `*` on region | Day-over-day change per region for Laptop Pro 15 |
| Laptop Pro 15 - Revenue YOY % | `*` on region | Year-over-year % per region for Laptop Pro 15 |
| Electronics Category - Revenue by Region | `*` on region | One row per region, all products in Electronics |
| Electronics - 10-Day Rolling Average by Region | `*` on region | Smoothed trend per region for Electronics |
| North America Region - All Products Revenue | Literal | Single row: North America total |
| Grand Total Revenue | `null` | Single number |
| Grand Total Units Sold | `null` | Single number |

### Refreshing a report

To regenerate a report for a specific date, trigger the task from the workflow UI for that date.

---

## Customizing the Pipeline

### Add a new dimension

Edit `dim_cube_config` in `01_cube_dynamic_transform.sql` to include the new dimension (e.g., `sales_channel`) with `include_in_cube = TRUE`. On the next run, all cube combinations including that dimension are computed automatically. Any template entry that uses `*` at that position will expand to include the new values without any template change.

### Add a new metric

Add an `INSERT` block to Stage 2 or Stage 3 following the existing pattern. The new metric key (e.g., `revenue_q10d`) is immediately available for any report template.

### Create a new report

Create a new JSON file following the same structure as `sales_performance_reporting.json`. Define a `metric_template` with the rows you want, using `*` where you want dynamic expansion. Add a companion `.leastaction.json` metadata file. Push to Git — the preAction imports it as a new task on the next run.

### Change the report style

Edit the `report_style` block in the report JSON:

```json
"report_style": {
  "theme": "corporate_blue",
  "header_bg_color": "#1565C0",
  "header_text_color": "#FFFFFF",
  "row_bg_color_even": "#f9f9f9",
  "row_hover_color": "#E3F2FD",
  "font_family": "Segoe UI, Arial, sans-serif"
}
```

---

## Files in the Package

| File | Purpose |
|------|---------|
| `00_fact_sales_daily.sql` | Create fact + dimension tables, generate random sales data |
| `01_cube_dynamic_transform.sql` | Cube config tables, helper functions, Stage 1 key-value aggregation |
| `02_stage2_metrics_dod_rolling.sql` | DOD, WOW, rolling windows, MTD, YTD metrics |
| `03_stage3_final_metrics_yoy_lookup.sql` | YOY, lookup, rank, penetration metrics; final table |
| `sales_performance_reporting.json` | Report payload — product & region dashboard |
| `sales_performance_reporting.json.leastaction.json` | Task metadata for the sales report |
| `category_performance_reporting.json` | Report payload — category & channel dashboard |
| `category_performance_reporting.json.leastaction.json` | Task metadata for the category report |
