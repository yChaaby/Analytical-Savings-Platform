{% macro cents_to_eur(column_name) -%}
    round(cast({{ column_name }} as decimal(18, 0)) / 100.0, 2)
{%- endmacro %}

{% macro normalize_email(column_name) -%}
    lower(trim({{ column_name }}))
{%- endmacro %}

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- elif target.name in ('prod', 'snowflake') -%}
        {{ custom_schema_name | trim }}
    {%- else -%}
        {{ target.schema }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}

{% macro last_value_ignore_nulls(expr) -%}
    {{ return(adapter.dispatch('last_value_ignore_nulls', 'alto_analytics')(expr)) }}
{%- endmacro %}
{% macro default__last_value_ignore_nulls(expr) -%} last_value({{ expr }} ignore nulls) {%- endmacro %}
{% macro snowflake__last_value_ignore_nulls(expr) -%} last_value({{ expr }}) ignore nulls {%- endmacro %}

{% macro first_value_ignore_nulls(expr) -%}
    {{ return(adapter.dispatch('first_value_ignore_nulls', 'alto_analytics')(expr)) }}
{%- endmacro %}
{% macro default__first_value_ignore_nulls(expr) -%} first_value({{ expr }} ignore nulls) {%- endmacro %}
{% macro snowflake__first_value_ignore_nulls(expr) -%} first_value({{ expr }}) ignore nulls {%- endmacro %}
