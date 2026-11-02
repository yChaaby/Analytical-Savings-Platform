select
    c.contrat_id,
    c.client_id,
    c.produit,
    p.libelle_produit,
    p.enveloppe,
    c.partenaire,
    c.reference_partenaire,
    c.profil_initial,
    c.mode_gestion,
    c.code_promo,
    p.taux_frais_mandat,
    p.taux_frais_enveloppe,
    p.fonds_euros_possible,
    c.ouvert_le,
    c.cloture_le,
    c.statut
from {{ ref('stg_app__contracts') }} as c
left join {{ ref('stg_app__products') }} as p using (produit)
