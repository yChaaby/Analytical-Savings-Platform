{% set inactivite = var('churn_inactivite_jours') %}

with clients as (
    select * from {{ ref('dim_clients') }}
    where statut_client = 'actif' and not est_mineur
),

arrete as (
    select * from {{ ref('int_date_arrete') }}
),

tickets_recents as (
    select
        email_demandeur                                                     as email,
        max(case when categorie in ('rachat', 'transfert') then 1 else 0 end) = 1 as ticket_rachat_recent
    from {{ ref('stg_zendesk__tickets') }}
    cross join arrete as a
    where cast(cree_le as date) > {{ dbt.dateadd('day', -90, 'a.date_arrete') }}
    group by 1
),

baisse_profil as (
    select distinct c.client_id
    from {{ ref('stg_app__mandate_changes') }} as m
    inner join {{ ref('stg_app__contracts') }} as c using (contrat_id)
    cross join arrete as a
    where m.nouveau_profil < m.profil_precedent
      and m.motif = 'demande_client'
      and cast(m.effectif_le as date) > {{ dbt.dateadd('day', -90, 'a.date_arrete') }}
),

signaux as (
    select
        c.client_id,
        c.email,
        c.segment_encours,
        c.encours_actuel_eur,
        coalesce(c.dernier_apport_le < {{ dbt.dateadd('day', -inactivite, 'a.date_arrete') }}, true) as s_inactivite,
        coalesce(c.dernier_rachat_partiel_le > {{ dbt.dateadd('day', -90, 'a.date_arrete') }}, false) as s_rachat_partiel,
        coalesce(t.ticket_rachat_recent, false)                                                       as s_ticket_rachat,
        c.nb_tickets_insatisfaits > 0                                                                 as s_insatisfaction,
        not coalesce(c.a_versement_programme_actif, false)                                            as s_sans_programme,
        b.client_id is not null                                                                       as s_baisse_profil
    from clients as c
    cross join arrete as a
    left join tickets_recents as t using (email)
    left join baisse_profil as b using (client_id)
),

score as (
    select
        *,
          case when s_inactivite then 15 else 0 end
        + case when s_rachat_partiel then 30 else 0 end
        + case when s_ticket_rachat then 25 else 0 end
        + case when s_insatisfaction then 10 else 0 end
        + case when s_sans_programme then 10 else 0 end
        + case when s_baisse_profil then 15 else 0 end                      as score_risque
    from signaux
)

select
    client_id,
    email,
    segment_encours,
    encours_actuel_eur,
    score_risque,
    case when score_risque >= 50 then 'eleve' when score_risque >= 30 then 'moyen' else 'faible' end as niveau_risque,
    concat_ws(', ',
        case when s_inactivite then 'aucun apport depuis {{ inactivite }} j' end,
        case when s_rachat_partiel then 'rachat partiel récent' end,
        case when s_ticket_rachat then 'ticket rachat/transfert récent' end,
        case when s_insatisfaction then 'ticket insatisfait' end,
        case when s_sans_programme then 'pas de versement programmé actif' end,
        case when s_baisse_profil then 'baisse de profil demandée' end
    )                                                                       as motifs,
    rank() over (order by score_risque * encours_actuel_eur desc)           as priorite_appel
from score
where score_risque >= 30
