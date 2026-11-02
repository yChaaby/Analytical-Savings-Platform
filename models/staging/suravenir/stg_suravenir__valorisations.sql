with source as (
    select * from {{ source('suravenir', 'valorisations') }}
    where not _fivetran_deleted
),

deduplicated as (
    select *
    from source
    qualify row_number() over (partition by num_contrat, date_valeur order by _fivetran_synced desc) = 1
)

select
    num_contrat                                 as reference_partenaire,
    cast(date_valeur as date)                   as date_valorisation,
    cast(montant_epargne as decimal(18, 2))     as encours_eur,
    cast(montant_uc as decimal(18, 2))          as encours_uc_eur,
    cast(montant_fonds_euros as decimal(18, 2)) as encours_fonds_euros_eur
from deduplicated
