with contrats_promo as (
    select c.contrat_id, c.client_id, c.produit, c.code_promo, c.ouvert_le, p.type_offre, p.plafond_eur
    from {{ ref('int_contrats_enrichis') }} as c
    inner join {{ ref('stg_app__promo_codes') }} as p using (code_promo)
),

versement_initial as (
    select contrat_id, montant_eur as versement_initial_eur
    from {{ ref('int_mouvements_executes') }}
    where type_mouvement in ('versement_initial', 'transfert_entrant')
    qualify row_number() over (partition by contrat_id order by execute_le, mouvement_id) = 1
),

palier as (
    select
        cp.*,
        vi.versement_initial_eur,
        pal.palier_min_eur,
        pal.nb_mois_rembourses,
        pal.prime_eur
    from contrats_promo as cp
    inner join versement_initial as vi using (contrat_id)
    inner join {{ ref('offres_paliers') }} as pal
        on pal.code_promo = cp.code_promo
       and vi.versement_initial_eur >= pal.palier_min_eur
    qualify row_number() over (partition by cp.contrat_id order by pal.palier_min_eur desc) = 1
),

mois_calendrier as (
    select date_day as mois
    from {{ ref('metricflow_time_spine') }}
    where date_day = cast(date_trunc('month', date_day) as date)
),

periodes as (
    select
        p.*,
        case
            when p.type_offre = 'prime'
                then cast({{ dbt.dateadd('month', 3, "date_trunc('month', p.ouvert_le)") }} as date)
            when extract(day from p.ouvert_le) = 1
                then cast(date_trunc('month', p.ouvert_le) as date)
            else cast({{ dbt.dateadd('month', 1, "date_trunc('month', p.ouvert_le)") }} as date)
        end                                                                     as premier_mois,
        case when p.type_offre = 'prime' then 1 else p.nb_mois_rembourses end   as nb_mois
    from palier as p
),

mois_offre as (
    select pe.*, m.mois
    from periodes as pe
    inner join mois_calendrier as m
        on m.mois >= pe.premier_mois
       and m.mois < {{ dbt.dateadd('month', 'pe.nb_mois', 'pe.premier_mois') }}
),

conditions as (
    select
        mo.*,
        a.apports_nets_cumules_eur,
        coalesce(a.apports_nets_cumules_eur >= mo.palier_min_eur - 0.01
                 and not a.est_cloture_fin_de_mois, false)                       as condition_respectee
    from mois_offre as mo
    left join {{ ref('int_apports_nets_mensuels') }} as a
        on a.contrat_id = mo.contrat_id
       and a.mois = mo.mois
),

rupture as (
    select
        *,
        min(case when not condition_respectee then mois end)
            over (partition by contrat_id)                                       as mois_rupture
    from conditions
),

montants as (
    select
        r.*,
        coalesce(f.frais_totaux_eur, 0)                                         as frais_du_mois_eur,
        (r.mois_rupture is null or r.mois < r.mois_rupture)                      as droit_ouvert
    from rupture as r
    left join {{ ref('int_frais_partenaires') }} as f
        on f.contrat_id = r.contrat_id
       and f.mois = r.mois
),

calcul as (
    select
        *,
        case
            when not droit_ouvert then 0
            when type_offre = 'prime' then prime_eur
            else frais_du_mois_eur
        end                                                                     as montant_brut_eur
    from montants
),

plafonne as (
    select
        *,
        sum(montant_brut_eur) over (
            partition by contrat_id order by mois
            rows between unbounded preceding and current row)                   as cumul_brut_eur
    from calcul
)

select
    contrat_id,
    client_id,
    produit,
    code_promo,
    type_offre,
    versement_initial_eur,
    palier_min_eur,
    mois                                                                        as mois_reference,
    last_day({{ dbt.dateadd('month', "case when type_offre = 'prime' then 0 else 1 end", 'mois') }}) as date_echeance,
    apports_nets_cumules_eur,
    condition_respectee,
    droit_ouvert,
    frais_du_mois_eur,
    round(least(montant_brut_eur, greatest(0, plafond_eur - (cumul_brut_eur - montant_brut_eur))), 2)
                                                                                as montant_du_eur
from plafonne
