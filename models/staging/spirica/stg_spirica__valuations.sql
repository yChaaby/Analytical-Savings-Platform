select
    policy_number                               as reference_partenaire,
    cast(nav_date as date)                      as date_valorisation,
    cast(total_value_eur as decimal(18, 2))     as encours_eur,
    cast(total_value_eur as decimal(18, 2))     as encours_uc_eur,
    cast(0 as decimal(18, 2))                   as encours_fonds_euros_eur
from {{ source('spirica', 'valuations') }}
where not _fivetran_deleted
