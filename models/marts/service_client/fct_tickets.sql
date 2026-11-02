select
    t.ticket_id,
    c.client_id,
    t.canal,
    t.categorie,
    t.statut,
    t.priorite,
    t.cree_le,
    cast(t.cree_le as date)                                                     as date_creation,
    t.resolu_le,
    round({{ dbt.datediff('t.cree_le', 't.resolu_le', 'minute') }} / 60.0, 1)   as delai_resolution_heures,
    t.satisfaction,
    c.client_id is not null                                                     as client_identifie
from {{ ref('stg_zendesk__tickets') }} as t
left join {{ ref('stg_app__clients') }} as c
    on t.email_demandeur = c.email
