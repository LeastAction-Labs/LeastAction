# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Source License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
_00 = '''\
/*
{
  "name": "00_fact_sales_daily.sql",
  "frequency": "0 2 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {}
}
*/

-- ============================================================================
-- CREATE FACT TABLE: fact_sales_daily
-- ============================================================================

DROP TABLE IF EXISTS fact_sales_daily CASCADE;

CREATE TABLE fact_sales_daily (
    sale_id BIGSERIAL,
    sale_date DATE NOT NULL,
    sale_timestamp TIMESTAMP NOT NULL,

    -- Product dimensions
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    product_sku VARCHAR(50),

    -- Category dimensions
    category_id VARCHAR(50) NOT NULL,
    category_name VARCHAR(100) NOT NULL,
    sub_category_id VARCHAR(50),
    sub_category_name VARCHAR(100),

    -- Customer dimensions
    customer_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_type VARCHAR(50),  -- 'Retail', 'Wholesale', 'Online'
    customer_segment VARCHAR(50),  -- 'Premium', 'Standard', 'Budget'

    -- Geographic dimensions
    region_id VARCHAR(50) NOT NULL,
    region_name VARCHAR(100) NOT NULL,
    sub_region_id VARCHAR(50),
    sub_region_name VARCHAR(100),
    country_id VARCHAR(50),
    country_name VARCHAR(100),
    state_id VARCHAR(50),
    state_name VARCHAR(100),
    city_id VARCHAR(50),
    city_name VARCHAR(100),

    -- Store dimensions
    store_id VARCHAR(50) NOT NULL,
    store_name VARCHAR(100) NOT NULL,
    store_type VARCHAR(50),  -- 'Flagship', 'Standard', 'Outlet'

    -- Channel dimensions
    sales_channel VARCHAR(50),  -- 'Online', 'In-Store', 'Phone', 'Mobile App'

    -- Measures
    revenue DECIMAL(15,2) NOT NULL,
    units_sold INTEGER NOT NULL,
    cost DECIMAL(15,2) NOT NULL,
    discount_amount DECIMAL(15,2) DEFAULT 0,
    shipping_cost DECIMAL(15,2) DEFAULT 0,
    tax_amount DECIMAL(15,2) DEFAULT 0,

    -- Calculated measures (can be computed)
    gross_profit DECIMAL(15,2) GENERATED ALWAYS AS (revenue - cost) STORED,
    net_revenue DECIMAL(15,2) GENERATED ALWAYS AS (revenue - discount_amount) STORED,
    profit_margin DECIMAL(6,2) GENERATED ALWAYS AS (
        CASE
            WHEN revenue > 0 THEN
                LEAST(((revenue - cost) / revenue * 100), 100.00)
            ELSE 0
        END
    ) STORED,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (sale_id)
);

-- Create indexes for performance
CREATE INDEX idx_fact_sales_date ON fact_sales_daily(sale_date);
CREATE INDEX idx_fact_sales_product ON fact_sales_daily(product_id);
CREATE INDEX idx_fact_sales_category ON fact_sales_daily(category_id);
CREATE INDEX idx_fact_sales_customer ON fact_sales_daily(customer_id);
CREATE INDEX idx_fact_sales_region ON fact_sales_daily(region_id);
CREATE INDEX idx_fact_sales_store ON fact_sales_daily(store_id);
CREATE INDEX idx_fact_sales_channel ON fact_sales_daily(sales_channel);
CREATE INDEX idx_fact_sales_composite ON fact_sales_daily(sale_date, product_id, store_id);

-- ============================================================================
-- LOOKUP TABLES FOR REFERENCE DATA
-- ============================================================================

-- Products lookup
DROP TABLE IF EXISTS dim_products CASCADE;
CREATE TABLE dim_products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    product_sku VARCHAR(50),
    category_id VARCHAR(50),
    sub_category_id VARCHAR(50)
);

-- Categories lookup
DROP TABLE IF EXISTS dim_categories CASCADE;
CREATE TABLE dim_categories (
    category_id VARCHAR(50) PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL,
    sub_category_id VARCHAR(50),
    sub_category_name VARCHAR(100)
);

-- Regions lookup
DROP TABLE IF EXISTS dim_regions CASCADE;
CREATE TABLE dim_regions (
    region_id VARCHAR(50) PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,
    sub_region_id VARCHAR(50),
    sub_region_name VARCHAR(100),
    country_id VARCHAR(50),
    country_name VARCHAR(100),
    state_id VARCHAR(50),
    state_name VARCHAR(100)
);

-- Stores lookup
DROP TABLE IF EXISTS dim_stores CASCADE;
CREATE TABLE dim_stores (
    store_id VARCHAR(50) PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL,
    store_type VARCHAR(50),
    region_id VARCHAR(50),
    city_id VARCHAR(50),
    city_name VARCHAR(100)
);

-- ============================================================================
-- STORED PROCEDURE: Generate Sample Data
-- Fixed version without COMMIT statements
-- ============================================================================

CREATE OR REPLACE PROCEDURE generate_sample_sales_data(
    p_num_rows INTEGER DEFAULT 10000000,
    p_start_date DATE DEFAULT '2023-01-01',
    p_end_date DATE DEFAULT CURRENT_DATE,
    p_batch_size INTEGER DEFAULT 100000
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_batch_count INTEGER;
    v_current_batch INTEGER := 0;
    v_rows_inserted INTEGER := 0;
    v_start_time TIMESTAMP;
    v_batch_start_time TIMESTAMP;
BEGIN
    v_start_time := clock_timestamp();
    v_batch_count := CEIL(p_num_rows::NUMERIC / p_batch_size);

    RAISE NOTICE 'Starting data generation...';
    RAISE NOTICE 'Target rows: %', p_num_rows;
    RAISE NOTICE 'Date range: % to %', p_start_date, p_end_date;
    RAISE NOTICE 'Batch size: %', p_batch_size;
    RAISE NOTICE 'Total batches: %', v_batch_count;
    RAISE NOTICE '----------------------------------------';

    -- Loop through batches
    FOR v_current_batch IN 1..v_batch_count LOOP
        v_batch_start_time := clock_timestamp();

        -- Insert batch
        INSERT INTO fact_sales_daily (
            sale_date,
            sale_timestamp,
            product_id,
            product_name,
            product_sku,
            category_id,
            category_name,
            sub_category_id,
            sub_category_name,
            customer_id,
            customer_name,
            customer_type,
            customer_segment,
            region_id,
            region_name,
            sub_region_id,
            sub_region_name,
            country_id,
            country_name,
            state_id,
            state_name,
            city_id,
            city_name,
            store_id,
            store_name,
            store_type,
            sales_channel,
            revenue,
            units_sold,
            cost,
            discount_amount,
            shipping_cost,
            tax_amount
        )
        SELECT
            -- Date (random within range)
            p_start_date + (RANDOM() * (p_end_date - p_start_date))::INTEGER AS sale_date,

            -- Timestamp (random time of day)
            (p_start_date + (RANDOM() * (p_end_date - p_start_date))::INTEGER)::TIMESTAMP
                + (RANDOM() * INTERVAL '24 hours') AS sale_timestamp,

            -- Product (100 products)
            'PROD_' || LPAD((RANDOM() * 99 + 1)::INTEGER::TEXT, 4, '0') AS product_id,
            CASE (RANDOM() * 99)::INTEGER % 10
                WHEN 0 THEN 'Laptop Pro 15'
                WHEN 1 THEN 'Wireless Mouse'
                WHEN 2 THEN 'USB-C Cable'
                WHEN 3 THEN 'Bluetooth Headphones'
                WHEN 4 THEN 'External SSD 1TB'
                WHEN 5 THEN 'Webcam HD'
                WHEN 6 THEN 'Mechanical Keyboard'
                WHEN 7 THEN 'Monitor 27 inch'
                WHEN 8 THEN 'Laptop Stand'
                ELSE 'Office Chair'
            END AS product_name,
            'SKU-' || LPAD((RANDOM() * 9999)::INTEGER::TEXT, 6, '0') AS product_sku,

            -- Category (10 categories)
            'CAT_' || LPAD((RANDOM() * 9 + 1)::INTEGER::TEXT, 2, '0') AS category_id,
            CASE (RANDOM() * 9)::INTEGER
                WHEN 0 THEN 'Electronics'
                WHEN 1 THEN 'Computers'
                WHEN 2 THEN 'Accessories'
                WHEN 3 THEN 'Furniture'
                WHEN 4 THEN 'Office Supplies'
                WHEN 5 THEN 'Peripherals'
                WHEN 6 THEN 'Storage'
                WHEN 7 THEN 'Audio'
                WHEN 8 THEN 'Video'
                ELSE 'Networking'
            END AS category_name,
            'SUBCAT_' || LPAD((RANDOM() * 29 + 1)::INTEGER::TEXT, 3, '0') AS sub_category_id,
            CASE (RANDOM() * 9)::INTEGER
                WHEN 0 THEN 'Premium Electronics'
                WHEN 1 THEN 'Gaming Computers'
                WHEN 2 THEN 'Wireless Accessories'
                WHEN 3 THEN 'Ergonomic Furniture'
                WHEN 4 THEN 'Paper Products'
                WHEN 5 THEN 'Input Devices'
                WHEN 6 THEN 'External Storage'
                WHEN 7 THEN 'Professional Audio'
                WHEN 8 THEN 'Streaming Video'
                ELSE 'Enterprise Network'
            END AS sub_category_name,

            -- Customer (1000 customers)
            'CUST_' || LPAD((RANDOM() * 999 + 1)::INTEGER::TEXT, 6, '0') AS customer_id,
            'Customer ' || LPAD((RANDOM() * 999 + 1)::INTEGER::TEXT, 6, '0') AS customer_name,
            CASE (RANDOM() * 2)::INTEGER
                WHEN 0 THEN 'Retail'
                WHEN 1 THEN 'Wholesale'
                ELSE 'Online'
            END AS customer_type,
            CASE (RANDOM() * 2)::INTEGER
                WHEN 0 THEN 'Premium'
                WHEN 1 THEN 'Standard'
                ELSE 'Budget'
            END AS customer_segment,

            -- Region (20 regions)
            'REG_' || LPAD((RANDOM() * 19 + 1)::INTEGER::TEXT, 2, '0') AS region_id,
            CASE (RANDOM() * 19)::INTEGER % 5
                WHEN 0 THEN 'North America'
                WHEN 1 THEN 'Europe'
                WHEN 2 THEN 'Asia Pacific'
                WHEN 3 THEN 'Latin America'
                ELSE 'Middle East Africa'
            END AS region_name,
            'SUBREG_' || LPAD((RANDOM() * 49 + 1)::INTEGER::TEXT, 3, '0') AS sub_region_id,
            CASE (RANDOM() * 9)::INTEGER
                WHEN 0 THEN 'Northeast USA'
                WHEN 1 THEN 'Western Europe'
                WHEN 2 THEN 'Southeast Asia'
                WHEN 3 THEN 'South America'
                WHEN 4 THEN 'Gulf States'
                WHEN 5 THEN 'Pacific Northwest'
                WHEN 6 THEN 'Eastern Europe'
                WHEN 7 THEN 'East Asia'
                WHEN 8 THEN 'Central America'
                ELSE 'North Africa'
            END AS sub_region_name,
            'COUNTRY_' || LPAD((RANDOM() * 49 + 1)::INTEGER::TEXT, 3, '0') AS country_id,
            CASE (RANDOM() * 9)::INTEGER
                WHEN 0 THEN 'United States'
                WHEN 1 THEN 'United Kingdom'
                WHEN 2 THEN 'Germany'
                WHEN 3 THEN 'France'
                WHEN 4 THEN 'Japan'
                WHEN 5 THEN 'China'
                WHEN 6 THEN 'Brazil'
                WHEN 7 THEN 'India'
                WHEN 8 THEN 'Australia'
                ELSE 'Canada'
            END AS country_name,
            'STATE_' || LPAD((RANDOM() * 99 + 1)::INTEGER::TEXT, 3, '0') AS state_id,
            CASE (RANDOM() * 9)::INTEGER
                WHEN 0 THEN 'California'
                WHEN 1 THEN 'New York'
                WHEN 2 THEN 'Texas'
                WHEN 3 THEN 'Florida'
                WHEN 4 THEN 'Illinois'
                WHEN 5 THEN 'Pennsylvania'
                WHEN 6 THEN 'Ohio'
                WHEN 7 THEN 'Georgia'
                WHEN 8 THEN 'Washington'
                ELSE 'Massachusetts'
            END AS state_name,
            'CITY_' || LPAD((RANDOM() * 499 + 1)::INTEGER::TEXT, 4, '0') AS city_id,
            CASE (RANDOM() * 9)::INTEGER
                WHEN 0 THEN 'New York'
                WHEN 1 THEN 'Los Angeles'
                WHEN 2 THEN 'Chicago'
                WHEN 3 THEN 'Houston'
                WHEN 4 THEN 'Phoenix'
                WHEN 5 THEN 'Philadelphia'
                WHEN 6 THEN 'San Antonio'
                WHEN 7 THEN 'San Diego'
                WHEN 8 THEN 'Dallas'
                ELSE 'San Francisco'
            END AS city_name,

            -- Store (500 stores)
            'STORE_' || LPAD((RANDOM() * 499 + 1)::INTEGER::TEXT, 5, '0') AS store_id,
            'Store ' || LPAD((RANDOM() * 499 + 1)::INTEGER::TEXT, 5, '0') AS store_name,
            CASE (RANDOM() * 2)::INTEGER
                WHEN 0 THEN 'Flagship'
                WHEN 1 THEN 'Standard'
                ELSE 'Outlet'
            END AS store_type,

            -- Channel
            CASE (RANDOM() * 3)::INTEGER
                WHEN 0 THEN 'Online'
                WHEN 1 THEN 'In-Store'
                WHEN 2 THEN 'Phone'
                ELSE 'Mobile App'
            END AS sales_channel,

            -- Measures (realistic ranges)
            (RANDOM() * 9900 + 100)::DECIMAL(15,2) AS revenue,  -- $100 to $10,000
            (RANDOM() * 9 + 1)::INTEGER AS units_sold,  -- 1 to 10 units
            (RANDOM() * 4900 + 50)::DECIMAL(15,2) AS cost,  -- $50 to $5,000
            (RANDOM() * 990 + 10)::DECIMAL(15,2) AS discount_amount,  -- $10 to $1,000
            (RANDOM() * 90 + 10)::DECIMAL(15,2) AS shipping_cost,  -- $10 to $100
            (RANDOM() * 490 + 10)::DECIMAL(15,2) AS tax_amount  -- $10 to $500
        FROM generate_series(1, LEAST(p_batch_size, p_num_rows - v_rows_inserted));

        v_rows_inserted := v_rows_inserted + p_batch_size;

        -- Progress report
        RAISE NOTICE 'Batch % of % complete (% rows) - Time: %',
            v_current_batch,
            v_batch_count,
            v_rows_inserted,
            clock_timestamp() - v_batch_start_time;

        -- Exit if we've inserted enough rows
        EXIT WHEN v_rows_inserted >= p_num_rows;
    END LOOP;

    -- Create statistics for better query performance
    ANALYZE fact_sales_daily;

    RAISE NOTICE '----------------------------------------';
    RAISE NOTICE 'Data generation complete!';
    RAISE NOTICE 'Total rows inserted: %', v_rows_inserted;
    RAISE NOTICE 'Total time: %', clock_timestamp() - v_start_time;
    RAISE NOTICE 'Average rate: % rows/second',
        ROUND(v_rows_inserted / EXTRACT(EPOCH FROM (clock_timestamp() - v_start_time)));

END;
$$;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: Generate 10 million rows (default)
-- CALL generate_sample_sales_data();

-- Example 2: Generate 1 million rows for testing
 CALL generate_sample_sales_data(p_num_rows := 100000);

-- Example 3: Generate 10 million rows for specific date range
-- CALL generate_sample_sales_data(
--     p_num_rows := 10000000,
--     p_start_date := '2023-01-01',
--     p_end_date := '2024-12-31'
-- );

-- Example 4: Generate with larger batch size for faster insertion
-- CALL generate_sample_sales_data(
--     p_num_rows := 10000000,
--     p_batch_size := 250000
-- );

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check total rows
-- SELECT COUNT(*) AS total_rows FROM fact_sales_daily;

-- Check date range
-- SELECT MIN(sale_date) AS min_date, MAX(sale_date) AS max_date FROM fact_sales_daily;

-- Check data distribution by dimension
-- SELECT
--     COUNT(DISTINCT product_id) AS products,
--     COUNT(DISTINCT category_id) AS categories,
--     COUNT(DISTINCT customer_id) AS customers,
--     COUNT(DISTINCT region_id) AS regions,
--     COUNT(DISTINCT store_id) AS stores
-- FROM fact_sales_daily;

-- Sample data preview
-- SELECT * FROM fact_sales_daily LIMIT 10;

-- Check revenue statistics
-- SELECT
--     COUNT(*) AS total_transactions,
--     ROUND(SUM(revenue)::NUMERIC, 2) AS total_revenue,
--     ROUND(AVG(revenue)::NUMERIC, 2) AS avg_revenue,
--     ROUND(MIN(revenue)::NUMERIC, 2) AS min_revenue,
--     ROUND(MAX(revenue)::NUMERIC, 2) AS max_revenue
-- FROM fact_sales_daily;
'''

_01 = '''\
/*
{
  "name": "01_cube_dynamic_transform.sql",
  "frequency": "0 2 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "00_fact_sales_daily.sql"
            }
          ]
        }
      }
    ]
  }
}
*/

-- ============================================================================
-- CONFIGURATION TABLE FOR CUBE GENERATION
-- ============================================================================
-- This table controls which dimension combinations to generate
-- Prevents data explosion by filtering unwanted combinations

DROP TABLE IF EXISTS dim_cube_config CASCADE;

CREATE TABLE dim_cube_config (
    config_id SERIAL PRIMARY KEY,
    config_name VARCHAR(100) NOT NULL UNIQUE,
    dimension_order INTEGER NOT NULL,  -- Order in which to evaluate (lower = higher priority)
    dimension_name VARCHAR(50) NOT NULL,
    dimension_column VARCHAR(50) NOT NULL,  -- Column name in fact table
    include_in_cube BOOLEAN DEFAULT TRUE,
    is_required BOOLEAN DEFAULT FALSE,  -- If true, must have a value (no NULL in CUBE)
    filter_values TEXT[],  -- Optional: only include these specific values
    exclude_values TEXT[],  -- Optional: exclude these specific values
    max_cardinality INTEGER,  -- Optional: max distinct values allowed
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert dimension configuration
-- Order matters: dimensions with lower order get higher priority in filtering
INSERT INTO dim_cube_config (config_name, dimension_order, dimension_name, dimension_column, include_in_cube, is_required, description) VALUES
('product', 1, 'product', 'product_name', TRUE, FALSE, 'Product dimension - always include'),
('category', 2, 'category', 'category_name', TRUE, FALSE, 'Category dimension'),
('region', 3, 'region', 'region_name', TRUE, FALSE, 'Region dimension'),
('sub_region', 4, 'sub_region', 'sub_region_name', TRUE, FALSE, 'Sub-region dimension - drill down from region'),
('store', 5, 'store', 'store_name', FALSE, FALSE, 'Store dimension - excluded by default to reduce cardinality');

-- Optional: Add filtering rules
-- Example: Only include specific products
-- UPDATE dim_cube_config 
-- SET filter_values = ARRAY['Product A', 'Product B', 'Product C']
-- WHERE config_name = 'product';

-- Example: Exclude test stores
-- UPDATE dim_cube_config 
-- SET exclude_values = ARRAY['Store Test', 'Store Demo']
-- WHERE config_name = 'store';

-- Example: Set max cardinality to prevent explosion
-- UPDATE dim_cube_config 
-- SET max_cardinality = 100
-- WHERE config_name = 'customer';

CREATE INDEX idx_cube_config_active ON dim_cube_config(active);
CREATE INDEX idx_cube_config_order ON dim_cube_config(dimension_order);

-- ============================================================================
-- CUBE FILTER RULES TABLE
-- ============================================================================
-- Define rules for which CUBE combinations to keep/exclude

DROP TABLE IF EXISTS dim_cube_filter_rules CASCADE;

CREATE TABLE dim_cube_filter_rules (
    rule_id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(20) NOT NULL,  -- 'KEEP' or 'EXCLUDE'
    rule_order INTEGER NOT NULL,  -- Order of evaluation
    dimension_pattern JSONB NOT NULL,  -- Pattern to match, e.g. {"product": "NOT NULL", "category": "NULL"}
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert filter rules
-- Rule: Keep combinations where product is specified (no product-level NULL)
INSERT INTO dim_cube_filter_rules (rule_name, rule_type, rule_order, dimension_pattern, description) VALUES
('require_product', 'KEEP', 1, '{"product": "NOT NULL"}', 'Always require product dimension - no product=NULL combinations'),
('no_subregion_without_region', 'EXCLUDE', 2, '{"region": "NULL", "sub_region": "NOT NULL"}', 'Cannot have sub-region without region'),
('no_store_without_region', 'EXCLUDE', 3, '{"region": "NULL", "store": "NOT NULL"}', 'Cannot have store without region');

-- Example additional rules (commented out):
-- Keep only specific patterns
-- INSERT INTO dim_cube_filter_rules (rule_name, rule_type, rule_order, dimension_pattern, description) VALUES
-- ('product_category_only', 'KEEP', 10, '{"product": "NOT NULL", "category": "NOT NULL", "region": "NULL"}', 'Keep product+category aggregates');

CREATE INDEX idx_cube_rules_active ON dim_cube_filter_rules(active);
CREATE INDEX idx_cube_rules_order ON dim_cube_filter_rules(rule_order);

-- ============================================================================
-- HELPER FUNCTION: Generate dim_key_grouping from CUBE result
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_dim_key_grouping(
    p_product TEXT,
    p_category TEXT,
    p_region TEXT,
    p_sub_region TEXT,
    p_store TEXT
) RETURNS TEXT AS $$
DECLARE
    result TEXT := '';
BEGIN
    -- Build hierarchical key with ::dim placeholder for NULLs
    result := COALESCE(p_product, 'dim_product');
    result := result || '::' || COALESCE(p_category, 'dim_category');
    result := result || '::' || COALESCE(p_region, 'dim_region');
    result := result || '::' || COALESCE(p_sub_region, 'dim_subregion');
    result := result || '::' || COALESCE(p_store, 'dim_store');
    
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- HELPER FUNCTION: Generate dim_value from actual values
-- ============================================================================

CREATE OR REPLACE FUNCTION generate_dim_value(
    p_product TEXT,
    p_category TEXT,
    p_region TEXT,
    p_sub_region TEXT,
    p_store TEXT
) RETURNS TEXT AS $$
DECLARE
    result TEXT := '';
    parts TEXT[] := ARRAY[]::TEXT[];
BEGIN
    -- Only include non-NULL values
    IF p_product IS NOT NULL THEN parts := array_append(parts, p_product); END IF;
    IF p_category IS NOT NULL THEN parts := array_append(parts, p_category); END IF;
    IF p_region IS NOT NULL THEN parts := array_append(parts, p_region); END IF;
    IF p_sub_region IS NOT NULL THEN parts := array_append(parts, p_sub_region); END IF;
    IF p_store IS NOT NULL THEN parts := array_append(parts, p_store); END IF;
    
    result := array_to_string(parts, '::', '');
    
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================================
-- HELPER FUNCTION: Check if CUBE combination passes filter rules
-- ============================================================================

CREATE OR REPLACE FUNCTION passes_cube_filters(
    p_product TEXT,
    p_category TEXT,
    p_region TEXT,
    p_sub_region TEXT,
    p_store TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    v_passes BOOLEAN := TRUE;
    v_rule RECORD;
BEGIN
    -- Check each active filter rule in order
    FOR v_rule IN 
        SELECT rule_type, dimension_pattern 
        FROM dim_cube_filter_rules 
        WHERE active = TRUE 
        ORDER BY rule_order
    LOOP
        -- For EXCLUDE rules: if pattern matches, reject
        IF v_rule.rule_type = 'EXCLUDE' THEN
            IF (
                -- Check each dimension in pattern
                (v_rule.dimension_pattern->>'product' = 'NULL' AND p_product IS NULL OR
                 v_rule.dimension_pattern->>'product' = 'NOT NULL' AND p_product IS NOT NULL OR
                 v_rule.dimension_pattern->>'product' IS NULL) AND
                (v_rule.dimension_pattern->>'category' = 'NULL' AND p_category IS NULL OR
                 v_rule.dimension_pattern->>'category' = 'NOT NULL' AND p_category IS NOT NULL OR
                 v_rule.dimension_pattern->>'category' IS NULL) AND
                (v_rule.dimension_pattern->>'region' = 'NULL' AND p_region IS NULL OR
                 v_rule.dimension_pattern->>'region' = 'NOT NULL' AND p_region IS NOT NULL OR
                 v_rule.dimension_pattern->>'region' IS NULL) AND
                (v_rule.dimension_pattern->>'sub_region' = 'NULL' AND p_sub_region IS NULL OR
                 v_rule.dimension_pattern->>'sub_region' = 'NOT NULL' AND p_sub_region IS NOT NULL OR
                 v_rule.dimension_pattern->>'sub_region' IS NULL) AND
                (v_rule.dimension_pattern->>'store' = 'NULL' AND p_store IS NULL OR
                 v_rule.dimension_pattern->>'store' = 'NOT NULL' AND p_store IS NOT NULL OR
                 v_rule.dimension_pattern->>'store' IS NULL)
            ) THEN
                RETURN FALSE;  -- Exclude this combination
            END IF;
        END IF;
        
        -- For KEEP rules: if pattern matches, keep (set flag)
        -- For KEEP rules: if NO patterns match by end, reject
        -- (Implementation can be extended)
    END LOOP;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- STAGE 1: TRANSFORM TO KEY-VALUE STRUCTURE USING CUBE
-- ============================================================================

DROP TABLE IF EXISTS fact_product_agg_daily_stage1 CASCADE;

CREATE TABLE fact_product_agg_daily_stage1 (
    date DATE NOT NULL,
    dim_key VARCHAR(200) NOT NULL,
    dim_key_grouping VARCHAR(200) NOT NULL,
    dim_value VARCHAR(500) NOT NULL,
    metric_key VARCHAR(50) NOT NULL,
    metric_value DECIMAL(15,2) NOT NULL,
    cube_level INTEGER,  -- How many dimensions are aggregated (NULLs in CUBE)
    PRIMARY KEY (date, dim_key_grouping, dim_value, metric_key)
);

-- Generate all CUBE combinations with filtering
INSERT INTO fact_product_agg_daily_stage1
WITH 
-- Get active dimensions configuration
active_dims AS (
    SELECT 
        dimension_name,
        dimension_column,
        dimension_order,
        include_in_cube,
        is_required,
        filter_values,
        exclude_values
    FROM dim_cube_config
    WHERE active = TRUE
    ORDER BY dimension_order
),
-- Apply dimension filters to base data
filtered_base AS (
    SELECT 
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        store_name,
        SUM(revenue) AS total_revenue,
        SUM(units_sold) AS total_units,
        SUM(cost) AS total_cost,
        SUM(discount_amount) AS total_discount
    FROM fact_sales_daily
    -- Apply filter_values and exclude_values from config
    -- (Simplified - in production, use dynamic SQL or more complex logic)
    GROUP BY 
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        store_name
),
-- Generate CUBE of all dimension combinations
cubed_data AS (
    SELECT 
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        store_name,
        SUM(total_revenue) AS total_revenue,
        SUM(total_units) AS total_units,
        SUM(total_cost) AS total_cost,
        SUM(total_discount) AS total_discount,
        -- Count how many dimensions are NULL (aggregation level)
        (CASE WHEN product_name IS NULL THEN 1 ELSE 0 END +
         CASE WHEN category_name IS NULL THEN 1 ELSE 0 END +
         CASE WHEN region_name IS NULL THEN 1 ELSE 0 END +
         CASE WHEN sub_region_name IS NULL THEN 1 ELSE 0 END +
         CASE WHEN store_name IS NULL THEN 1 ELSE 0 END) AS cube_level
    FROM filtered_base
    GROUP BY CUBE(
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        store_name
    )
    HAVING 
        -- Apply filter rules
        passes_cube_filters(
            product_name,
            category_name,
            region_name,
            sub_region_name,
            store_name
        ) = TRUE
        -- Exclude combinations based on config
        AND (
            -- If store not included in cube, exclude store-level combinations
            (SELECT include_in_cube FROM dim_cube_config WHERE dimension_name = 'store') = TRUE
            OR store_name IS NULL
        )
        -- Exclude full aggregation (all NULLs) - usually not needed
        AND NOT (
            product_name IS NULL AND 
            category_name IS NULL AND 
            region_name IS NULL AND 
            sub_region_name IS NULL AND 
            store_name IS NULL
        )
),
-- Transform to key-value structure
transformed AS (
    -- Revenue metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'revenue' AS metric_key,
        total_revenue AS metric_value,
        cube_level
    FROM cubed_data
    
    UNION ALL
    
    -- Units sold metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'units_sold' AS metric_key,
        total_units AS metric_value,
        cube_level
    FROM cubed_data
    
    UNION ALL
    
    -- Cost metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'cost' AS metric_key,
        total_cost AS metric_value,
        cube_level
    FROM cubed_data
    
    UNION ALL
    
    -- Profit metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'profit' AS metric_key,
        total_revenue - total_cost AS metric_value,
        cube_level
    FROM cubed_data
    
    UNION ALL
    
    -- Discount metric
    SELECT 
        sale_date AS date,
        'dim_product::dim_category::dim_region::dim_subregion::dim_store' AS dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name, store_name) AS dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name, store_name) AS dim_value,
        'discount' AS metric_key,
        total_discount AS metric_value,
        cube_level
    FROM cubed_data
)
SELECT * FROM transformed where date is not null;

CREATE INDEX idx_stage1_date ON fact_product_agg_daily_stage1(date);
CREATE INDEX idx_stage1_grouping ON fact_product_agg_daily_stage1(dim_key_grouping);
CREATE INDEX idx_stage1_metric ON fact_product_agg_daily_stage1(metric_key);
CREATE INDEX idx_stage1_cube_level ON fact_product_agg_daily_stage1(cube_level);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Show cube combinations generated
-- SELECT
--     cube_level,
--     COUNT(*) AS combination_count,
--     COUNT(DISTINCT dim_key_grouping) AS unique_groupings,
--     AVG(metric_value) AS avg_value
-- FROM fact_product_agg_daily_stage1
-- WHERE metric_key = 'revenue'
-- GROUP BY cube_level
-- ORDER BY cube_level;
--
-- -- Show sample groupings at each cube level
-- SELECT DISTINCT
--     cube_level,
--     dim_key_grouping,
--     dim_value
-- FROM fact_product_agg_daily_stage1
-- WHERE metric_key = 'revenue'
--   AND date = (SELECT MAX(date) FROM fact_product_agg_daily_stage1)
-- ORDER BY cube_level, dim_key_grouping
-- LIMIT 50;
--
-- -- Show total records
-- SELECT
--     'Total Records' AS metric,
--     COUNT(*) AS count
-- FROM fact_product_agg_daily_stage1
-- UNION ALL
-- SELECT
--     'Unique Groupings',
--     COUNT(DISTINCT dim_key_grouping)
-- FROM fact_product_agg_daily_stage1
-- UNION ALL
-- SELECT
--     'Unique Dim Values',
--     COUNT(DISTINCT dim_value)
-- FROM fact_product_agg_daily_stage1
-- UNION ALL
-- SELECT
--     'Date Range (days)',
--     COUNT(DISTINCT date)
-- FROM fact_product_agg_daily_stage1;
--
-- -- Show sample
-- SELECT *
-- FROM fact_product_agg_daily_stage1
--  where metric_key <> 'revenue' and cube_level = 1
-- LIMIT 50;
--
--
-- SELECT *
-- FROM fact_product_agg_daily_stage1
-- where metric_key = 'revenue'  and cube_level = 1
-- LIMIT 50;
--
'''

_02 = '''\
/*
{
  "name": "02_stage2_metrics_dod_rolling.sql",
  "frequency": "0 2 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "01_cube_dynamic_transform.sql"
            }
          ]
        }
      }
    ]
  }
}
*/

-- ============================================================================
-- STAGE 2 METRICS: DAY-OVER-DAY AND ROLLING STATISTICS
-- ============================================================================
-- These metrics require only the base data from Stage 1
-- Run each metric SQL separately for better manageability

-- ============================================================================
-- METRIC 1: DOD (Day-Over-Day Change)
-- ============================================================================
-- Calculate day-over-day change for each metric
-- Formula: current_value - previous_day_value

DROP TABLE IF EXISTS fact_product_agg_daily_stage2 CASCADE;

CREATE TABLE fact_product_agg_daily_stage2 AS
SELECT * FROM fact_product_agg_daily_stage1;

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 1) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_day_value
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit', 'cost')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_dod' AS metric_key,
    COALESCE(metric_value - prev_day_value, 0) AS metric_value
FROM metric_with_lag
WHERE prev_day_value IS NOT NULL;  -- Skip first day (no previous value)

-- ============================================================================
-- METRIC 2: DOD Percentage (Day-Over-Day Percentage Change)
-- ============================================================================
-- Calculate day-over-day percentage change
-- Formula: ((current_value - previous_day_value) / previous_day_value) * 100

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 1) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_day_value
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_dod_pct' AS metric_key,
    CASE 
        WHEN prev_day_value = 0 THEN 0
        ELSE ((metric_value - prev_day_value) / NULLIF(prev_day_value, 0)) * 100
    END AS metric_value
FROM metric_with_lag
WHERE prev_day_value IS NOT NULL;

-- ============================================================================
-- METRIC 3: WOW (Week-Over-Week Change)
-- ============================================================================
-- Calculate week-over-week change (7 days back)
-- Formula: current_value - value_7_days_ago

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 7) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_week_value
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_wow' AS metric_key,
    COALESCE(metric_value - prev_week_value, 0) AS metric_value
FROM metric_with_lag
WHERE prev_week_value IS NOT NULL;

-- ============================================================================
-- METRIC 4: STD_10D (10-Day Rolling Standard Deviation)
-- ============================================================================
-- Calculate rolling 10-day standard deviation
-- Useful for volatility analysis

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        STDDEV(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS std_10d
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_std_10d' AS metric_key,
    COALESCE(std_10d, 0) AS metric_value
FROM rolling_window;

-- ============================================================================
-- METRIC 5: AVG_10D (10-Day Rolling Average)
-- ============================================================================
-- Calculate rolling 10-day average
-- Smooths out daily fluctuations

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        AVG(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS avg_10d
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_avg_10d' AS metric_key,
    COALESCE(avg_10d, 0) AS metric_value
FROM rolling_window;

-- ============================================================================
-- METRIC 6: MIN_10D (10-Day Rolling Minimum)
-- ============================================================================
-- Calculate rolling 10-day minimum

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        MIN(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS min_10d
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_min_10d' AS metric_key,
    COALESCE(min_10d, 0) AS metric_value
FROM rolling_window;

-- ============================================================================
-- METRIC 7: MAX_10D (10-Day Rolling Maximum)
-- ============================================================================
-- Calculate rolling 10-day maximum

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        MAX(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS max_10d
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_max_10d' AS metric_key,
    COALESCE(max_10d, 0) AS metric_value
FROM rolling_window;

-- ============================================================================
-- METRIC 8: SUM_10D (10-Day Rolling Sum)
-- ============================================================================
-- Calculate rolling 10-day sum
-- Useful for "last 10 days total" metrics

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH rolling_window AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        SUM(metric_value) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS sum_10d
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_sum_10d' AS metric_key,
    COALESCE(sum_10d, 0) AS metric_value
FROM rolling_window;

-- ============================================================================
-- METRIC 9: MTD (Month-To-Date)
-- ============================================================================
-- Calculate month-to-date cumulative sum

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH mtd_calc AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        SUM(metric_value) OVER (
            PARTITION BY 
                dim_key_grouping, 
                dim_value, 
                metric_key,
                DATE_TRUNC('month', date)
            ORDER BY date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS mtd_sum
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_mtd' AS metric_key,
    COALESCE(mtd_sum, 0) AS metric_value
FROM mtd_calc;

-- ============================================================================
-- METRIC 10: YTD (Year-To-Date)
-- ============================================================================
-- Calculate year-to-date cumulative sum

INSERT INTO fact_product_agg_daily_stage2 (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH ytd_calc AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        SUM(metric_value) OVER (
            PARTITION BY 
                dim_key_grouping, 
                dim_value, 
                metric_key,
                DATE_TRUNC('year', date)
            ORDER BY date 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS ytd_sum
    FROM fact_product_agg_daily_stage1
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_ytd' AS metric_key,
    COALESCE(ytd_sum, 0) AS metric_value
FROM ytd_calc;

-- Verify Stage 2 data
--SELECT
--    metric_key,
--    COUNT(*) AS record_count,
--    MIN(date) AS min_date,
--    MAX(date) AS max_date,
--    AVG(metric_value) AS avg_value
--FROM fact_product_agg_daily_stage2
--GROUP BY metric_key
--ORDER BY metric_key;

-- Verify Stage 2 data
--SELECT *
--FROM fact_product_agg_daily_stage2
--LIMIT 100

'''

_03 = '''\
/*
{
  "name": "03_stage3_final_metrics_yoy_lookup.sql",
  "frequency": "0 2 * * *",
  "operator_name": "PostgresqlExecuteSQL",
  "connection_name": "postgresql",
  "partition": "{{partition}}",
  "config_name": [],
  "start_date": "2026-01-01",
  "end_date": "2026-12-31",
  "over_ride": true,
  "config": {},
  "actions": {
    "pre_actions": [
      {
        "name": "LeastActionCheckIfParentsAreDone",
        "action_variables": {
          "parents": [
            {
              "account_laui": "{{account_laui}}",
              "project_laui": "{{project_laui}}",
              "partition": "{{partition}}",
              "task_name": "02_stage2_metrics_dod_rolling.sql"
            }
          ]
        }
      }
    ]
  }
}
*/

-- ============================================================================
-- STAGE 3 (FINAL): YEAR-OVER-YEAR AND LOOKUP METRICS
-- ============================================================================
-- These metrics require Stage 2 data (especially DOD metrics)
-- This creates the final table: fact_product_agg_daily

DROP TABLE IF EXISTS fact_product_agg_daily CASCADE;

CREATE TABLE fact_product_agg_daily AS
SELECT * FROM fact_product_agg_daily_stage2;

ALTER TABLE fact_product_agg_daily 
ADD PRIMARY KEY (date, dim_key_grouping, dim_value, metric_key);

CREATE INDEX idx_final_date ON fact_product_agg_daily(date);
CREATE INDEX idx_final_grouping ON fact_product_agg_daily(dim_key_grouping);
CREATE INDEX idx_final_metric ON fact_product_agg_daily(metric_key);



-- ============================================================================
-- METRIC 1: YOY (Year-Over-Year Change)
-- ============================================================================
-- Calculate year-over-year change (365 days back)
-- Formula: current_value - value_365_days_ago

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_year_value
    FROM fact_product_agg_daily_stage2
    WHERE metric_key IN ('revenue', 'units_sold', 'profit', 'cost')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_yoy' AS metric_key,
    COALESCE(metric_value - prev_year_value, 0) AS metric_value
FROM metric_with_lag
WHERE prev_year_value IS NOT NULL;

-- ============================================================================
-- METRIC 2: YOY Percentage
-- ============================================================================
-- Calculate year-over-year percentage change

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH metric_with_lag AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_year_value
    FROM fact_product_agg_daily_stage2
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_yoy_pct' AS metric_key,
    CASE 
        WHEN prev_year_value = 0 THEN 0
        ELSE ((metric_value - prev_year_value) / NULLIF(prev_year_value, 0)) * 100
    END AS metric_value
FROM metric_with_lag
WHERE prev_year_value IS NOT NULL;

-- ============================================================================
-- METRIC 3: DODLY (Day-Over-Day Last Year)
-- ============================================================================
-- Compare today's DOD with DOD from same day last year
-- This requires the DOD metric from Stage 2

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH dod_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS dod_last_year
    FROM fact_product_agg_daily_stage2
    WHERE metric_key LIKE '%_dod' 
      AND metric_key NOT LIKE '%_dod_pct'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_dod', '_dodly') AS metric_key,
    COALESCE(metric_value - dod_last_year, 0) AS metric_value
FROM dod_current
WHERE dod_last_year IS NOT NULL;

-- ============================================================================
-- METRIC 4: DODLY Percentage
-- ============================================================================
-- Percentage change in DOD compared to last year's DOD

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH dod_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS dod_last_year
    FROM fact_product_agg_daily_stage2
    WHERE metric_key LIKE '%_dod' 
      AND metric_key NOT LIKE '%_dod_pct'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_dod', '_dodly_pct') AS metric_key,
    CASE 
        WHEN dod_last_year = 0 THEN 0
        ELSE ((metric_value - dod_last_year) / NULLIF(ABS(dod_last_year), 0)) * 100
    END AS metric_value
FROM dod_current
WHERE dod_last_year IS NOT NULL;

-- ============================================================================
-- METRIC 5: STD_10D_YOY (10-Day STD Year-Over-Year)
-- ============================================================================
-- Compare current 10-day volatility to last year's

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH std_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS std_last_year
    FROM fact_product_agg_daily_stage2
    WHERE metric_key LIKE '%_std_10d'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_std_10d', '_std_10d_yoy') AS metric_key,
    COALESCE(metric_value - std_last_year, 0) AS metric_value
FROM std_current
WHERE std_last_year IS NOT NULL;

-- ============================================================================
-- METRIC 6: AVG_10D_VS_YOY (Compare 10-Day Average to Last Year)
-- ============================================================================
-- Compare current 10-day average to last year's same period

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH avg_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS avg_last_year
    FROM fact_product_agg_daily_stage2
    WHERE metric_key LIKE '%_avg_10d'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_avg_10d', '_avg_10d_yoy') AS metric_key,
    COALESCE(metric_value - avg_last_year, 0) AS metric_value
FROM avg_current
WHERE avg_last_year IS NOT NULL;

-- ============================================================================
-- METRIC 7: PREV_YEAR_SAME_DATE (Lookup Last Year's Value)
-- ============================================================================
-- Simple lookup of last year's value for the same date

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH prev_year_lookup AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_year_value
    FROM fact_product_agg_daily_stage2
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_ly' AS metric_key,
    COALESCE(prev_year_value, 0) AS metric_value
FROM prev_year_lookup
WHERE prev_year_value IS NOT NULL;

-- ============================================================================
-- METRIC 8: PREV_WEEK_SAME_DAY (Lookup Last Week's Same Day)
-- ============================================================================
-- Lookup value from same day of week, previous week

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH prev_week_lookup AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        LAG(metric_value, 7) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS prev_week_value
    FROM fact_product_agg_daily_stage2
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_lw' AS metric_key,
    COALESCE(prev_week_value, 0) AS metric_value
FROM prev_week_lookup
WHERE prev_week_value IS NOT NULL;

-- ============================================================================
-- METRIC 9: MTD_YOY (Month-to-Date Year-Over-Year)
-- ============================================================================
-- Compare current MTD to last year's MTD for same period

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH mtd_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS mtd_last_year
    FROM fact_product_agg_daily_stage2
    WHERE metric_key LIKE '%_mtd'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_mtd', '_mtd_yoy') AS metric_key,
    COALESCE(metric_value - mtd_last_year, 0) AS metric_value
FROM mtd_current
WHERE mtd_last_year IS NOT NULL;

-- ============================================================================
-- METRIC 10: YTD_YOY (Year-to-Date Year-Over-Year)
-- ============================================================================
-- Compare current YTD to last year's YTD for same period

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH ytd_current AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        metric_value,
        LAG(metric_value, 365) OVER (
            PARTITION BY dim_key_grouping, dim_value, metric_key 
            ORDER BY date
        ) AS ytd_last_year
    FROM fact_product_agg_daily_stage2
    WHERE metric_key LIKE '%_ytd'
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    REPLACE(metric_key, '_ytd', '_ytd_yoy') AS metric_key,
    COALESCE(metric_value - ytd_last_year, 0) AS metric_value
FROM ytd_current
WHERE ytd_last_year IS NOT NULL;

-- ============================================================================
-- METRIC 11: RANK_DAILY (Daily Rank within Group)
-- ============================================================================
-- Rank each dimension value within its grouping for each day

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH ranked AS (
    SELECT 
        date,
        dim_key,
        dim_key_grouping,
        dim_value,
        metric_key,
        RANK() OVER (
            PARTITION BY date, dim_key_grouping, metric_key
            ORDER BY metric_value DESC
        ) AS rank_value
    FROM fact_product_agg_daily_stage2
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_rank' AS metric_key,
    rank_value AS metric_value
FROM ranked;

-- ============================================================================
-- METRIC 12: PENETRATION (Metric as % of Total)
-- ============================================================================
-- Calculate what % this dimension represents of the total

INSERT INTO fact_product_agg_daily (date, dim_key, dim_key_grouping, dim_value, metric_key, metric_value)
WITH totals AS (
    SELECT 
        date,
        dim_key_grouping,
        metric_key,
        SUM(metric_value) AS total_value
    FROM fact_product_agg_daily_stage2
    WHERE metric_key IN ('revenue', 'units_sold', 'profit')
    GROUP BY date, dim_key_grouping, metric_key
),
with_totals AS (
    SELECT 
        f.date,
        f.dim_key,
        f.dim_key_grouping,
        f.dim_value,
        f.metric_key,
        f.metric_value,
        t.total_value
    FROM fact_product_agg_daily_stage2 f
    INNER JOIN totals t 
        ON f.date = t.date 
        AND f.dim_key_grouping = t.dim_key_grouping 
        AND f.metric_key = t.metric_key
    WHERE f.metric_key IN ('revenue', 'units_sold', 'profit')
)
SELECT 
    date,
    dim_key,
    dim_key_grouping,
    dim_value,
    metric_key || '_pct_of_total' AS metric_key,
    CASE 
        WHEN total_value = 0 THEN 0
        ELSE (metric_value / NULLIF(total_value, 0)) * 100
    END AS metric_value
FROM with_totals;

-- ============================================================================
-- Final Verification
-- ============================================================================

-- -- Count records per metric
-- SELECT
--     metric_key,
--     COUNT(*) AS record_count,
--     MIN(date) AS min_date,
--     MAX(date) AS max_date,
--     ROUND(AVG(metric_value)::NUMERIC, 2) AS avg_value,
--     ROUND(MIN(metric_value)::NUMERIC, 2) AS min_value,
--     ROUND(MAX(metric_value)::NUMERIC, 2) AS max_value
-- FROM fact_product_agg_daily
-- GROUP BY metric_key
-- ORDER BY metric_key;
--
-- -- Summary statistics
-- SELECT
--     COUNT(DISTINCT date) AS total_dates,
--     COUNT(DISTINCT dim_key_grouping) AS total_groupings,
--     COUNT(DISTINCT dim_value) AS total_dim_values,
--     COUNT(DISTINCT metric_key) AS total_metrics,
--     COUNT(*) AS total_records
-- FROM fact_product_agg_daily;
--
-- -- Sample data
-- SELECT *
-- FROM fact_product_agg_daily
-- WHERE date = (SELECT MAX(date) FROM fact_product_agg_daily)
-- LIMIT 20;
'''

payloads = {
    "00_fact_sales_daily.sql":             _00,
    "01_cube_dynamic_transform.sql":       _01,
    "02_stage2_metrics_dod_rolling.sql":   _02,
    "03_stage3_final_metrics_yoy_lookup.sql": _03,
}

skills = {
    "00_fact_sales_daily.md": """\
# Step 0 — Create Fact Table & Generate Sample Data

Drops and recreates `fact_sales_daily` — the raw transaction table that drives the entire pipeline.
Also creates lookup tables (`dim_products`, `dim_categories`, `dim_regions`, `dim_stores`) and
calls `generate_sample_sales_data(p_num_rows := 100000)` to populate 100K rows of realistic
synthetic sales data.

## Schema — fact_sales_daily
| Column group | Columns |
|---|---|
| Date | `sale_date`, `sale_timestamp` |
| Product | `product_id`, `product_name`, `product_sku` |
| Category | `category_id`, `category_name`, `sub_category_id/name` |
| Customer | `customer_id`, `customer_name`, `customer_type`, `customer_segment` |
| Geography | `region_id/name`, `sub_region_id/name`, `country`, `state`, `city` |
| Store | `store_id`, `store_name`, `store_type` |
| Channel | `sales_channel` |
| Measures | `revenue`, `units_sold`, `cost`, `discount_amount`, `shipping_cost`, `tax_amount` |
| Computed | `gross_profit`, `net_revenue`, `profit_margin` (GENERATED STORED) |

## Adapting this step
- **Row count**: Change `p_num_rows := 100000` to any target. Default procedure supports up to 10M rows with batching.
- **Date range**: Change `p_start_date` / `p_end_date` arguments to `generate_sample_sales_data`.
- **Real data**: Replace the `CALL generate_sample_sales_data(...)` with an `INSERT INTO fact_sales_daily SELECT ...` from your source tables, matching the column list.
- **No DROP**: Remove the `DROP TABLE IF EXISTS` lines if you want incremental loads instead of full refresh.

## No dependencies
This step has no pre_actions — it always runs first.
""",

    "01_cube_dynamic_transform.md": """\
# Step 1 — Cube Config & Stage 1 Aggregation

Creates two control tables (`dim_cube_config`, `dim_cube_filter_rules`), helper functions, and
`fact_product_agg_daily_stage1` — a key-value metric store built from a filtered PostgreSQL `CUBE`
over the fact table.

## What the CUBE does
Generates every combination of (product, category, region, sub_region, store) aggregations —
i.e. total by product only, total by product+category, total by region, grand total, etc.
Each combination becomes a row with a `dim_key_grouping` (which dimensions are populated) and
`dim_value` (their actual values joined by `::`).

## Metrics produced (per dimension combination, per date)
`revenue`, `units_sold`, `cost`, `profit`, `discount`

## Control tables
| Table | Purpose |
|---|---|
| `dim_cube_config` | Which dimensions to include in the CUBE and their cardinality limits |
| `dim_cube_filter_rules` | KEEP/EXCLUDE rules to prune nonsensical combinations (e.g. sub_region without region) |

## Adapting this step
- **Add/remove dimensions**: Insert/delete rows in `dim_cube_config`. Update the `CUBE(...)` clause and the `generate_dim_*` functions to match.
- **Reduce cardinality**: Set `include_in_cube = FALSE` for high-cardinality dimensions (e.g. store) to shrink the output.
- **Add filter rules**: Insert into `dim_cube_filter_rules` with `rule_type = 'EXCLUDE'` and a `dimension_pattern` JSONB object.
- **Add metrics**: Add more `UNION ALL` blocks in the `transformed` CTE inside the INSERT statement.

## Dependency
Waits for `00_fact_sales_daily.sql` (`LeastActionCheckIfParentsAreDone`).
""",

    "02_stage2_metrics_dod_rolling.md": """\
# Step 2 — Stage 2: DOD, WOW & Rolling Window Metrics

Extends Stage 1 by computing time-series derived metrics using window functions.
Creates `fact_product_agg_daily_stage2` as a copy of Stage 1, then appends 10 new metric families.

## Metrics added (all computed per dimension combination)
| Metric suffix | Formula | Window |
|---|---|---|
| `_dod` | current − previous day | LAG(1) |
| `_dod_pct` | DOD as % of previous day | LAG(1) |
| `_wow` | current − 7 days ago | LAG(7) |
| `_std_10d` | 10-day rolling standard deviation | ROWS 9 PRECEDING |
| `_avg_10d` | 10-day rolling average | ROWS 9 PRECEDING |
| `_min_10d` | 10-day rolling minimum | ROWS 9 PRECEDING |
| `_max_10d` | 10-day rolling maximum | ROWS 9 PRECEDING |
| `_sum_10d` | 10-day rolling sum | ROWS 9 PRECEDING |
| `_mtd` | Month-to-date cumulative sum | UNBOUNDED PRECEDING within month |
| `_ytd` | Year-to-date cumulative sum | UNBOUNDED PRECEDING within year |

## Base metrics used as input
`revenue`, `units_sold`, `profit`, `cost` (from Stage 1).

## Adapting this step
- **Change window size**: Replace `9 PRECEDING` with `N-1 PRECEDING` for an N-day window.
- **Add a new metric**: Add an `INSERT INTO fact_product_agg_daily_stage2` block with a new window function and suffix.
- **Skip a metric**: Remove the corresponding INSERT block.

## Dependency
Waits for `01_cube_dynamic_transform.sql` (`LeastActionCheckIfParentsAreDone`).
""",

    "03_stage3_final_metrics_yoy_lookup.md": """\
# Step 3 — Stage 3 (Final): YOY, Lookup & Rank Metrics

Creates the final output table `fact_product_agg_daily` from Stage 2, then appends 12 more metric
families that require a full year of history (YOY) or Stage 2 derived metrics (DODLY).

## Metrics added
| Metric suffix | Description |
|---|---|
| `_yoy` | Year-over-year absolute change (LAG 365 days) |
| `_yoy_pct` | Year-over-year percentage change |
| `_dodly` | DOD change vs same day last year |
| `_dodly_pct` | DODLY as percentage |
| `_std_10d_yoy` | 10-day volatility vs last year |
| `_avg_10d_yoy` | 10-day average vs last year |
| `_ly` | Last year's value (lookup) |
| `_lw` | Last week's value (lookup) |
| `_mtd_yoy` | MTD vs last year's MTD |
| `_ytd_yoy` | YTD vs last year's YTD |
| `_rank` | Daily rank within grouping by metric |
| `_pct_of_total` | Dimension's share of group total (%) |

## Final output
`fact_product_agg_daily` — the single table consumed by downstream reports and the
`PostgresqlGenerateHtmlTableReport` operator tasks.

## Adapting this step
- **YOY with leap year**: Change `LAG(365)` to `LAG(366)` for leap-year-aware comparison, or use a date join.
- **Add a rank**: Add a `RANK() OVER (PARTITION BY date, dim_key_grouping, metric_key ORDER BY metric_value DESC)` block.
- **Report configs**: After this step succeeds, the `PostgresqlGenerateHtml_config_product` and `PostgresqlGenerateHtml_config_category` payload configs drive HTML report generation via the `PostgresqlGenerateHtmlTableReport` operator.

## Dependency
Waits for `02_stage2_metrics_dod_rolling.sql` (`LeastActionCheckIfParentsAreDone`).
""",
}

prompt = (
    "Four-step PostgreSQL sales reporting pipeline: "
    "(0) create fact_sales_daily and generate 100K synthetic rows across products, categories, regions, stores and channels; "
    "(1) build a configurable CUBE aggregation into fact_product_agg_daily_stage1 (key-value metric store); "
    "(2) compute DOD, WOW, rolling 10-day stats, MTD and YTD into fact_product_agg_daily_stage2; "
    "(3) compute YOY, DODLY, rank and penetration metrics into the final fact_product_agg_daily table. "
    "All steps run daily at 2am via PostgresqlExecuteSQL on a postgresql connection, "
    "linked by LeastActionCheckIfParentsAreDone dependency chains."
)

description = (
    "End-to-end PostgreSQL sales analytics pipeline: synthetic data generation → CUBE aggregation → "
    "rolling/time-series metrics → YOY/rank/penetration final table. "
    "Produces fact_product_agg_daily consumed by HTML report operators."
)

guide_docs = """\
# Sales Cube Transform Usecase

> SQL-native transformation (Transformation stage). This builds the sales cube mart only; for the
> transform **plus** HTML reports see `postgresql-sales-reporting`, and for the dbt-invocation variant see
> `dbt-sales-reporting`.

## What it does
Builds a complete sales analytics data mart in PostgreSQL across 4 sequential steps,
producing `fact_product_agg_daily` — a key-value metric store queryable by any
dimension combination (product, category, region, sub-region) and any metric key.

| Step | File | Output table | What it does |
|------|------|---|---|
| 0 | `00_fact_sales_daily.sql` | `fact_sales_daily` | Creates fact table + 100K synthetic rows |
| 1 | `01_cube_dynamic_transform.sql` | `fact_product_agg_daily_stage1` | CUBE aggregation → key-value metrics |
| 2 | `02_stage2_metrics_dod_rolling.sql` | `fact_product_agg_daily_stage2` | DOD / WOW / rolling stats / MTD / YTD |
| 3 | `03_stage3_final_metrics_yoy_lookup.sql` | `fact_product_agg_daily` | YOY / DODLY / rank / penetration |

## Prerequisites
- Operator `PostgresqlExecuteSQL` must exist in core
- Connection named `postgresql` must exist and point to a live PostgreSQL instance
- Action `LeastActionCheckIfParentsAreDone` must exist in core
- For HTML reports: operator `PostgresqlGenerateHtmlTableReport` and payload configs
  `PostgresqlGenerateHtml_config_product` / `PostgresqlGenerateHtml_config_category` must exist

## Template variables
| Variable | Description |
|---|---|
| `{{partition}}` | Task partition key |
| `{{account_laui}}` | LAUI of the account folder (resolved at runtime) |
| `{{project_laui}}` | LAUI of the project folder (resolved at runtime) |

## Metric naming convention
All metrics in `fact_product_agg_daily` follow `<base>_<suffix>`:
- Base: `revenue`, `units_sold`, `profit`, `cost`, `discount`
- Suffixes: `_dod`, `_dod_pct`, `_wow`, `_std_10d`, `_avg_10d`, `_min_10d`, `_max_10d`,
  `_sum_10d`, `_mtd`, `_ytd`, `_yoy`, `_yoy_pct`, `_dodly`, `_dodly_pct`,
  `_std_10d_yoy`, `_avg_10d_yoy`, `_ly`, `_lw`, `_mtd_yoy`, `_ytd_yoy`, `_rank`, `_pct_of_total`

## Deploying
Use the **Usecase Deploy Skill** in the LeastAction AI assistant:
> "deploy usecase PostgresqlSalesReportingDemo"

The assistant will present the step table, ask for your connection and date range, then create all four tasks in order.
"""

publisher = "LeastAction"

metadata = {
    "service": "PostgreSQL",
    "category": "Transformation",
    "tags": [
        "flavor:S+P", "lifecycle:transformation", "sql-native",
        "postgresql", "sales", "analytics", "usecase",
        "cube", "kpi", "dod", "yoy", "rolling", "pipeline",
    ],
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"],
}
