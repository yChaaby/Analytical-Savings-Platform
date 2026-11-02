{{ config(materialized='table') }}
select
    max(date_valorisation)                                          as date_arrete,
    last_day(max(date_valorisation))                                as fin_mois_arrete,
    cast(date_trunc('month', min(date_valorisation)) as date)       as debut_donnees
from {{ ref('int_valorisations_unifiees') }}
