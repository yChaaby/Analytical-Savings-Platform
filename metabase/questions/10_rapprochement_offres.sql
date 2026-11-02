-- name: Rapprochement des offres promotionnelles (droits et paiements)
-- display: table
select
    code_promo,
    statut_rapprochement,
    count(*)                        as lignes,
    round(sum(montant_du_eur), 2)   as du_eur,
    round(sum(montant_paye_eur), 2) as paye_eur,
    round(sum(ecart_eur), 2)        as ecart_eur
from analytics.finance.finance_offres_rapprochement
where statut_rapprochement <> 'sans_objet'
group by 1, 2
order by 1, 2
