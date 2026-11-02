-- name: Écarts de frais à traiter avec les partenaires
-- display: table
select
    partenaire,
    diagnostic,
    count(*)                                                    as contrats_mois,
    round(sum(ecart_frais_mandat_eur + ecart_frais_enveloppe_eur), 2) as ecart_total_eur,
    min(mois)                                                   as premier_mois,
    max(mois)                                                   as dernier_mois
from analytics.finance.finance_rapprochement_frais
group by 1, 2
order by 1, 2
