with contrats as (
    select contrat_id, ouvert_le, cloture_le from {{ ref('int_contrats_enrichis') }}
),

arrete as (
    select * from {{ ref('int_date_arrete') }}
),

mois as (
    select date_day as mois
    from {{ ref('metricflow_time_spine') }}
    where date_day = cast(date_trunc('month', date_day) as date)
),

grille as (
    select c.contrat_id, m.mois, c.cloture_le
    from contrats as c
    cross join arrete as a
    inner join mois as m
        on m.mois between cast(date_trunc('month', c.ouvert_le) as date) and a.fin_mois_arrete
),

flux_mensuels as (
    select
        contrat_id,
        cast(date_trunc('month', date_execution) as date)   as mois,
        sum(montant_signe_eur)                              as apports_nets_mois_eur
    from {{ ref('int_mouvements_executes') }}
    group by 1, 2
)

select
    g.contrat_id,
    g.mois,
    coalesce(f.apports_nets_mois_eur, 0)                                as apports_nets_mois_eur,
    sum(coalesce(f.apports_nets_mois_eur, 0)) over (
        partition by g.contrat_id order by g.mois
        rows between unbounded preceding and current row)               as apports_nets_cumules_eur,
    coalesce(cast(g.cloture_le as date) <= last_day(g.mois), false)     as est_cloture_fin_de_mois
from grille as g
left join flux_mensuels as f using (contrat_id, mois)
