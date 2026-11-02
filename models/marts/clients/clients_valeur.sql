with clients as (
    select * from {{ ref('dim_clients') }}
    where statut_client in ('actif', 'parti')
),

arrete as (
    select * from {{ ref('int_date_arrete') }}
),

revenus as (
    select client_id, sum(revenu_net_eur) as revenu_frais_eur
    from {{ ref('fct_frais_mensuels') }}
    group by 1
),

primes as (
    select client_id, sum(montant_du_eur) as primes_eur
    from {{ ref('fct_offres_droits') }}
    where type_offre = 'prime' and statut_echeance = 'echu'
    group by 1
),

revenu_courant as (
    select
        c.client_id,
        sum(case when c.statut = 'open' then e.encours_uc_eur * c.taux_frais_mandat else 0 end) as revenu_annuel_courant_eur
    from {{ ref('dim_contrats') }} as c
    cross join arrete as a
    left join {{ ref('fct_encours_quotidien') }} as e
        on e.contrat_id = c.contrat_id
       and e.date_valorisation = a.date_arrete
    group by 1
),

retention as (
    select
        1 - (
            sum(case when date_churn > {{ dbt.dateadd('month', -12, 'a.date_arrete') }} then 1 else 0 end) * 1.0
            / nullif(sum(case when cast(premier_contrat_le as date) <= {{ dbt.dateadd('month', -12, 'a.date_arrete') }}
                               and (date_churn is null or date_churn > {{ dbt.dateadd('month', -12, 'a.date_arrete') }})
                              then 1 else 0 end), 0)
        )                                                                   as taux_retention_annuel
    from {{ ref('dim_clients') }}
    cross join arrete as a
)

select
    c.client_id,
    c.canal_acquisition,
    c.produit_entree,
    c.code_promo_entree,
    c.tranche_age,
    c.segment_encours,
    c.statut_client,
    c.encours_actuel_eur,
    round(coalesce(r.revenu_frais_eur, 0) - coalesce(p.primes_eur, 0), 2)  as revenu_historique_eur,
    round(coalesce(rc.revenu_annuel_courant_eur, 0), 2)                     as revenu_annuel_courant_eur,
    round(ret.taux_retention_annuel, 4)                                     as taux_retention_annuel,
    round(coalesce(rc.revenu_annuel_courant_eur, 0) * (
          power(ret.taux_retention_annuel / 1.08, 1) + power(ret.taux_retention_annuel / 1.08, 2)
        + power(ret.taux_retention_annuel / 1.08, 3) + power(ret.taux_retention_annuel / 1.08, 4)
        + power(ret.taux_retention_annuel / 1.08, 5)), 2)                  as valeur_projetee_5ans_eur
from clients as c
left join revenus as r using (client_id)
left join primes as p using (client_id)
left join revenu_courant as rc using (client_id)
cross join retention as ret
