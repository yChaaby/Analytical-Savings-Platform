with contrats as (
    select * from {{ ref('int_contrats_enrichis') }}
),

arrete as (
    select * from {{ ref('int_date_arrete') }}
),

valorisations as (
    select contrat_id, date_valorisation, encours_uc_eur
    from {{ ref('int_valorisations_unifiees') }}
),

premier_apport as (
    select contrat_id, min(date_execution) as date_premier_apport
    from {{ ref('int_mouvements_executes') }}
    where sens = 'apport'
    group by 1
),

bornes as (
    select
        c.contrat_id,
        case
            when cast(c.ouvert_le as date) < a.debut_donnees
            then {{ dbt.dateadd('day', -1, 'a.debut_donnees') }}
            else p.date_premier_apport
        end                                                         as debut,
        coalesce(cast(c.cloture_le as date), a.fin_mois_arrete)     as fin
    from contrats as c
    cross join arrete as a
    inner join premier_apport as p using (contrat_id)
),

jours as (
    select b.contrat_id, s.date_day
    from bornes as b
    inner join {{ ref('metricflow_time_spine') }} as s
        on s.date_day between b.debut and b.fin
),

encours_complete as (
    select
        j.contrat_id,
        j.date_day,
        coalesce(
            {{ last_value_ignore_nulls('v.encours_uc_eur') }} over (
                partition by j.contrat_id order by j.date_day
                rows between unbounded preceding and current row),
            {{ first_value_ignore_nulls('v.encours_uc_eur') }} over (
                partition by j.contrat_id order by j.date_day
                rows between current row and unbounded following)
        )                                                           as encours_uc_eur
    from jours as j
    left join valorisations as v
        on j.contrat_id = v.contrat_id
       and j.date_day = v.date_valorisation
),

frais_jour as (
    select
        e.contrat_id,
        e.date_day,
        lag(e.encours_uc_eur) over (partition by e.contrat_id order by e.date_day)   as encours_uc_veille
    from encours_complete as e
),

theoriques as (
    select
        f.contrat_id,
        cast(date_trunc('month', f.date_day) as date)                               as mois,
        sum(coalesce(f.encours_uc_veille, 0) * c.taux_frais_mandat / 365.0)          as frais_mandat_theoriques_eur,
        sum(coalesce(f.encours_uc_veille, 0) * c.taux_frais_enveloppe / 365.0)       as frais_enveloppe_theoriques_eur,
        avg(f.encours_uc_veille)                                                    as encours_uc_moyen_eur
    from frais_jour as f
    inner join contrats as c using (contrat_id)
    group by 1, 2
)

select
    coalesce(t.contrat_id, p.contrat_id)                                as contrat_id,
    coalesce(t.mois, p.mois)                                            as mois,
    round(t.encours_uc_moyen_eur, 2)                                    as encours_uc_moyen_eur,
    round(coalesce(t.frais_mandat_theoriques_eur, 0), 2)                as frais_mandat_theoriques_eur,
    round(coalesce(t.frais_enveloppe_theoriques_eur, 0), 2)             as frais_enveloppe_theoriques_eur,
    coalesce(p.frais_mandat_eur, 0)                                     as frais_mandat_preleves_eur,
    coalesce(p.frais_enveloppe_eur, 0)                                  as frais_enveloppe_preleves_eur
from theoriques as t
full outer join {{ ref('int_frais_partenaires') }} as p
    on t.contrat_id = p.contrat_id
   and t.mois = p.mois
