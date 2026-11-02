select
    id                                          as changement_id,
    contract_id                                 as contrat_id,
    previous_profile                            as profil_precedent,
    new_profile                                 as nouveau_profil,
    reason                                      as motif,
    cast(effective_at as timestamp)             as effectif_le
from {{ source('app', 'mandate_changes') }}
where not _fivetran_deleted
