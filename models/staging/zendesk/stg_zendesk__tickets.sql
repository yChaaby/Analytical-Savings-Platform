select
    id                                          as ticket_id,
    {{ normalize_email('requester_email') }}    as email_demandeur,
    channel                                     as canal,
    category                                    as categorie,
    status                                      as statut,
    priority                                    as priorite,
    cast(created_at as timestamp)               as cree_le,
    cast(solved_at as timestamp)                as resolu_le,
    satisfaction_rating                         as satisfaction
from {{ source('zendesk', 'tickets') }}
where not _fivetran_deleted
