select
    partenaire,
    mois,
    contrat_id,
    client_id,
    produit,
    encours_uc_moyen_eur,
    frais_mandat_theoriques_eur,
    frais_mandat_preleves_eur,
    ecart_frais_mandat_eur,
    frais_enveloppe_theoriques_eur,
    frais_enveloppe_preleves_eur,
    ecart_frais_enveloppe_eur,
    case
        when frais_mandat_preleves_eur = 0 and frais_enveloppe_preleves_eur = 0 then 'ligne_absente'
        when abs(ecart_frais_mandat_eur / nullif(frais_mandat_theoriques_eur, 0) - 0.1429) < 0.02
            then 'taux_mandat_errone'
        when ecart_frais_mandat_eur + ecart_frais_enveloppe_eur > 0 then 'sur_prelevement'
        else 'sous_prelevement'
    end                                                                     as diagnostic
from {{ ref('fct_frais_mensuels') }}
where ecart_a_investiguer
