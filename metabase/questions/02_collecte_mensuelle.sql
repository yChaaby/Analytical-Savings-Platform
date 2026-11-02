-- name: Collecte brute, rachats et collecte nette par mois
-- display: bar
select
    date_trunc('month', date_execution)                                 as mois,
    sum(case when sens = 'apport' then montant_eur else 0 end)          as collecte_brute_eur,
    -sum(case when sens = 'retrait' then montant_eur else 0 end)        as rachats_eur,
    sum(montant_signe_eur)                                              as collecte_nette_eur
from analytics.finance.fct_mouvements
where date_execution >= '2022-01-01'
group by 1
order by 1
