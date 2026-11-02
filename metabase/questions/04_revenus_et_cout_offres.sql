-- name: Revenus de mandat et coût des offres par mois
-- display: line
select
    mois,
    sum(frais_mandat_preleves_eur)  as revenus_mandat_eur,
    sum(cout_offres_eur)            as cout_offres_eur,
    sum(revenu_net_eur)             as revenus_nets_eur
from analytics.finance.fct_frais_mensuels
group by 1
order by 1
