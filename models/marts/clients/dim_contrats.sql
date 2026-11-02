with derniere_valo as (
    select contrat_id, encours_eur, encours_uc_eur
    from {{ ref('fct_encours_quotidien') }}
    qualify row_number() over (partition by contrat_id order by date_valorisation desc) = 1
),

profil_actuel as (
    select contrat_id, profil
    from {{ ref('int_profil_contrat_historique') }}
    where est_actuel
)

select
    c.contrat_id,
    c.client_id,
    c.produit,
    c.libelle_produit,
    c.enveloppe,
    c.partenaire,
    pt.nom_partenaire,
    c.profil_initial,
    pa.profil                                                           as profil_actuel,
    c.mode_gestion,
    c.code_promo,
    c.taux_frais_mandat,
    c.taux_frais_enveloppe,
    c.ouvert_le,
    cast(c.ouvert_le as date)                                           as date_ouverture,
    c.cloture_le,
    cast(c.cloture_le as date)                                          as date_cloture,
    c.statut,
    case when c.statut = 'open' then coalesce(v.encours_eur, 0) else 0 end as encours_actuel_eur
from {{ ref('int_contrats_enrichis') }} as c
left join derniere_valo as v using (contrat_id)
left join profil_actuel as pa using (contrat_id)
left join {{ ref('partenaires') }} as pt using (partenaire)
