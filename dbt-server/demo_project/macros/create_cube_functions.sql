{% macro create_cube_functions() %}

CREATE OR REPLACE FUNCTION generate_dim_key_grouping(
    p_product TEXT,
    p_category TEXT,
    p_region TEXT,
    p_sub_region TEXT
) RETURNS TEXT AS $$
BEGIN
    RETURN COALESCE(p_product, 'dim_product')
        || '::' || COALESCE(p_category, 'dim_category')
        || '::' || COALESCE(p_region, 'dim_region')
        || '::' || COALESCE(p_sub_region, 'dim_subregion');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION generate_dim_value(
    p_product TEXT,
    p_category TEXT,
    p_region TEXT,
    p_sub_region TEXT
) RETURNS TEXT AS $$
DECLARE
    parts TEXT[] := ARRAY[]::TEXT[];
BEGIN
    IF p_product IS NOT NULL THEN parts := array_append(parts, p_product); END IF;
    IF p_category IS NOT NULL THEN parts := array_append(parts, p_category); END IF;
    IF p_region IS NOT NULL THEN parts := array_append(parts, p_region); END IF;
    IF p_sub_region IS NOT NULL THEN parts := array_append(parts, p_sub_region); END IF;
    RETURN array_to_string(parts, '::', '');
END;
$$ LANGUAGE plpgsql IMMUTABLE;

{% endmacro %}
