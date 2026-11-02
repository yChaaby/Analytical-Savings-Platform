with source as (
    select * from {{ source('app', 'movements') }}
    where not _fivetran_deleted
),

deduplicated as (
    select *
    from source
    qualify row_number() over (partition by id order by _fivetran_synced desc) = 1
)

select
    id                                          as mouvement_id,
    contract_id                                 as contrat_id,
    movement_type                               as type_mouvement,
    case
        when movement_type like 'rachat%' then 'retrait'
        else 'apport'
    end                                         as sens,
    {{ cents_to_eur('amount_cents') }}          as montant_eur,
    status                                      as statut,
    cast(requested_at as timestamp)             as demande_le,
    cast(executed_at as timestamp)              as execute_le
from deduplicated
