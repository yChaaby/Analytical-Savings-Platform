{% set tol = var('rapprochement_frais_tolerance_pct') %}

with frais as (
    select * from {{ ref('int_frais_mensuels_contrats') }}
),

remboursements as (
    select contrat_id, mois_reference as mois, sum(montant_du_eur) as cout_offres_eur
    from {{ ref('int_offres_droits') }}
    where type_offre = 'remboursement_frais'
    group by 1, 2
)

select
    f.contrat_id,
    c.client_id,
    c.produit,
    c.enveloppe,
    c.partenaire,
    f.mois,
    f.encours_uc_moyen_eur,
    f.frais_mandat_theoriques_eur,
    f.frais_mandat_preleves_eur,
    f.frais_enveloppe_theoriques_eur,
    f.frais_enveloppe_preleves_eur,
    round(f.frais_mandat_preleves_eur - f.frais_mandat_theoriques_eur, 2)             as ecart_frais_mandat_eur,
    round(f.frais_enveloppe_preleves_eur - f.frais_enveloppe_theoriques_eur, 2)       as ecart_frais_enveloppe_eur,
    coalesce(r.cout_offres_eur, 0)                                                    as cout_offres_eur,
    round(f.frais_mandat_preleves_eur - coalesce(r.cout_offres_eur, 0), 2)            as revenu_net_eur,
    (
        abs(f.frais_mandat_preleves_eur - f.frais_mandat_theoriques_eur)
            > greatest(1, {{ tol }} * f.frais_mandat_theoriques_eur)
        or abs(f.frais_enveloppe_preleves_eur - f.frais_enveloppe_theoriques_eur)
            > greatest(1, {{ tol }} * f.frais_enveloppe_theoriques_eur)
    )                                                                                 as ecart_a_investiguer
from frais as f
inner join {{ ref('int_contrats_enrichis') }} as c using (contrat_id)
left join remboursements as r using (contrat_id, mois)
