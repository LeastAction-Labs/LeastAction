{{ config(materialized='table') }}

with filtered_base as (
    select
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        sum(revenue) as total_revenue,
        sum(units_sold) as total_units,
        sum(cost) as total_cost,
        sum(discount_amount) as total_discount
    from {{ source('sales', 'fact_sales_daily') }}
    group by sale_date, product_name, category_name, region_name, sub_region_name
),

cubed_data as (
    select
        sale_date,
        product_name,
        category_name,
        region_name,
        sub_region_name,
        sum(total_revenue) as total_revenue,
        sum(total_units) as total_units,
        sum(total_cost) as total_cost,
        sum(total_discount) as total_discount,
        (case when product_name is null then 1 else 0 end +
         case when category_name is null then 1 else 0 end +
         case when region_name is null then 1 else 0 end +
         case when sub_region_name is null then 1 else 0 end) as cube_level
    from filtered_base
    group by cube(sale_date, product_name, category_name, region_name, sub_region_name)
    having sale_date is not null
),

transformed as (
    select sale_date as date,
        'dim_product::dim_category::dim_region::dim_subregion' as dim_key,
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name) as dim_key_grouping,
        generate_dim_value(product_name, category_name, region_name, sub_region_name) as dim_value,
        'revenue' as metric_key, total_revenue as metric_value, cube_level
    from cubed_data
    union all
    select sale_date, 'dim_product::dim_category::dim_region::dim_subregion',
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name),
        generate_dim_value(product_name, category_name, region_name, sub_region_name),
        'units_sold', total_units, cube_level
    from cubed_data
    union all
    select sale_date, 'dim_product::dim_category::dim_region::dim_subregion',
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name),
        generate_dim_value(product_name, category_name, region_name, sub_region_name),
        'cost', total_cost, cube_level
    from cubed_data
    union all
    select sale_date, 'dim_product::dim_category::dim_region::dim_subregion',
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name),
        generate_dim_value(product_name, category_name, region_name, sub_region_name),
        'profit', total_revenue - total_cost, cube_level
    from cubed_data
    union all
    select sale_date, 'dim_product::dim_category::dim_region::dim_subregion',
        generate_dim_key_grouping(product_name, category_name, region_name, sub_region_name),
        generate_dim_value(product_name, category_name, region_name, sub_region_name),
        'discount', total_discount, cube_level
    from cubed_data
)

select * from transformed
