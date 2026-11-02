with clients as (
    select * from {{ ref('stg_app__clients') }}
),

arrete as (
    select * from {{ ref('int_date_arrete') }}
),

contrats as (
    select
        client_id,
        min(ouvert_le)                                                          as premier_contrat_le,
        count(*)                                                                as nb_contrats,
        sum(case when statut = 'open' then 1 else 0 end)                        as nb_contrats_ouverts,
        count(distinct case when statut = 'open' then enveloppe end)            as nb_enveloppes_detenues,
        max(case when statut = 'open' and enveloppe = 'assurance_vie' then 1 else 0 end) = 1 as detient_assurance_vie,
        max(case when statut = 'open' and enveloppe = 'per' then 1 else 0 end) = 1           as detient_per,
        max(case when statut = 'open' and enveloppe = 'pea' then 1 else 0 end) = 1           as detient_pea,
        max(case when statut = 'open' and enveloppe = 'cto' then 1 else 0 end) = 1           as detient_cto,
        sum(encours_actuel_eur)                                                 as encours_actuel_eur,
        case when sum(case when statut = 'open' then 1 else 0 end) = 0
             then max(cloture_le) end                                           as churn_le
    from {{ ref('dim_contrats') }}
    group by 1
),

premier_contrat as (
    select client_id, produit as produit_entree, code_promo as code_promo_entree
    from {{ ref('dim_contrats') }}
    qualify row_number() over (partition by client_id order by ouvert_le, contrat_id) = 1
),

flux as (
    select
        client_id,
        sum(case when sens = 'apport' then montant_eur else 0 end)              as total_apports_eur,
        sum(case when sens = 'retrait' then montant_eur else 0 end)             as total_retraits_eur,
        max(case when sens = 'apport' then date_execution end)                  as dernier_apport_le,
        max(case when type_mouvement = 'rachat_partiel' then date_execution end) as dernier_rachat_partiel_le,
        max(case when type_mouvement = 'versement_programme' then date_execution end) as dernier_versement_programme_le
    from {{ ref('int_mouvements_executes') }}
    group by 1
),

tickets as (
    select
        email_demandeur                                                         as email,
        count(*)                                                                as nb_tickets,
        sum(case when satisfaction = 'bad' then 1 else 0 end)                   as nb_tickets_insatisfaits
    from {{ ref('stg_zendesk__tickets') }}
    group by 1
),

crm as (
    select email, max(case when optin_newsletter then 1 else 0 end) = 1         as optin_newsletter
    from {{ ref('stg_crm__contacts') }}
    group by 1
)

select
    c.client_id,
    c.email,
    c.prenom,
    c.nom,
    c.est_mineur,
    c.representant_legal_id,
    c.canal_acquisition,
    c.parrain_client_id,
    c.categorie_socio_pro,
    c.tranche_revenus,
    c.tranche_patrimoine_financier,
    c.objectif_placement,
    c.profil_recommande,
    c.statut_kyc,
    c.inscrit_le,
    cast(c.inscrit_le as date)                                                  as date_inscription,
    floor({{ dbt.datediff('c.date_naissance', 'a.date_arrete', 'day') }} / 365.25) as age,
    case
        when c.est_mineur then 'mineur'
        when floor({{ dbt.datediff('c.date_naissance', 'a.date_arrete', 'day') }} / 365.25) < 30 then '18-29'
        when floor({{ dbt.datediff('c.date_naissance', 'a.date_arrete', 'day') }} / 365.25) < 40 then '30-39'
        when floor({{ dbt.datediff('c.date_naissance', 'a.date_arrete', 'day') }} / 365.25) < 50 then '40-49'
        when floor({{ dbt.datediff('c.date_naissance', 'a.date_arrete', 'day') }} / 365.25) < 60 then '50-59'
        else '60+'
    end                                                                         as tranche_age,
    ct.premier_contrat_le,
    pc.produit_entree,
    pc.code_promo_entree,
    cast(ct.churn_le as date)                                                   as date_churn,
    coalesce(ct.nb_contrats, 0)                                                 as nb_contrats,
    coalesce(ct.nb_contrats_ouverts, 0)                                         as nb_contrats_ouverts,
    coalesce(ct.nb_enveloppes_detenues, 0)                                      as nb_enveloppes_detenues,
    coalesce(ct.detient_assurance_vie, false)                                   as detient_assurance_vie,
    coalesce(ct.detient_per, false)                                             as detient_per,
    coalesce(ct.detient_pea, false)                                             as detient_pea,
    coalesce(ct.detient_cto, false)                                             as detient_cto,
    coalesce(ct.encours_actuel_eur, 0)                                          as encours_actuel_eur,
    case
        when coalesce(ct.encours_actuel_eur, 0) = 0       then 'sans_encours'
        when ct.encours_actuel_eur < 10000                then 'moins_10k'
        when ct.encours_actuel_eur < 50000                then '10k_50k'
        when ct.encours_actuel_eur < 100000               then '50k_100k'
        else 'gestion_privee_100k_plus'
    end                                                                         as segment_encours,
    coalesce(f.total_apports_eur, 0)                                            as total_apports_eur,
    coalesce(f.total_retraits_eur, 0)                                           as total_retraits_eur,
    f.dernier_apport_le,
    f.dernier_rachat_partiel_le,
    f.dernier_versement_programme_le >= {{ dbt.dateadd('day', -45, 'a.date_arrete') }}  as a_versement_programme_actif,
    coalesce(t.nb_tickets, 0)                                                   as nb_tickets,
    coalesce(t.nb_tickets_insatisfaits, 0)                                      as nb_tickets_insatisfaits,
    coalesce(cr.optin_newsletter, false)                                        as optin_newsletter,
    case
        when c.statut_kyc <> 'validated'      then 'prospect'
        when ct.client_id is null             then 'inscrit_sans_contrat'
        when ct.nb_contrats_ouverts > 0       then 'actif'
        else 'parti'
    end                                                                         as statut_client
from clients as c
cross join arrete as a
left join contrats as ct using (client_id)
left join premier_contrat as pc using (client_id)
left join flux as f using (client_id)
left join tickets as t using (email)
left join crm as cr using (email)
