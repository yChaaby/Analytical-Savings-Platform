with droits as (
    select
        contrat_id, client_id, code_promo, type_offre,
        case when type_offre = 'prime' then 'prime' else cast(mois_reference as varchar) end  as cle_periode,
        mois_reference,
        montant_du_eur
    from {{ ref('fct_offres_droits') }}
    where statut_echeance = 'echu'
),

paiements as (
    select
        contrat_id, code_promo,
        case when type_paiement = 'prime' then 'prime' else cast(mois_reference as varchar) end as cle_periode,
        count(*)                as nb_paiements,
        sum(montant_eur)        as montant_paye_eur,
        max(paye_le)            as dernier_paiement_le
    from {{ ref('stg_app__promo_payments') }}
    where statut = 'paid'
    group by 1, 2, 3
),

rapproche as (
    select
        coalesce(d.contrat_id, p.contrat_id)            as contrat_id,
        d.client_id,
        coalesce(d.code_promo, p.code_promo)            as code_promo,
        d.type_offre,
        coalesce(d.cle_periode, p.cle_periode)          as cle_periode,
        coalesce(d.montant_du_eur, 0)                   as montant_du_eur,
        coalesce(p.montant_paye_eur, 0)                 as montant_paye_eur,
        coalesce(p.nb_paiements, 0)                     as nb_paiements,
        p.dernier_paiement_le
    from droits as d
    full outer join paiements as p
        on d.contrat_id = p.contrat_id
       and d.code_promo = p.code_promo
       and d.cle_periode = p.cle_periode
)

select
    *,
    round(montant_paye_eur - montant_du_eur, 2)                                     as ecart_eur,
    case
        when montant_du_eur = 0 and montant_paye_eur = 0                then 'sans_objet'
        when nb_paiements > 1                                           then 'doublon'
        when montant_du_eur > 0 and nb_paiements = 0                    then 'non_paye'
        when montant_du_eur = 0 and montant_paye_eur > 0                then 'paye_a_tort'
        when abs(montant_paye_eur - montant_du_eur) <= 0.01             then 'conforme'
        else 'ecart_montant'
    end                                                                             as statut_rapprochement
from rapproche
