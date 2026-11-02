with source as (
    select * from {{ source('ca_titres', 'positions') }}
    where not _fivetran_deleted
),

deduplicated as (
    select *
    from source
    qualify row_number() over (partition by compte, date_position order by _fivetran_synced desc) = 1
)

select
    compte                                                      as reference_partenaire,
    cast(date_position as date)                                 as date_valorisation,
    cast(valorisation_titres + solde_especes as decimal(18, 2))  as encours_eur,
    cast(valorisation_titres + solde_especes as decimal(18, 2))  as encours_uc_eur,
    cast(0 as decimal(18, 2))                                   as encours_fonds_euros_eur
from deduplicated
