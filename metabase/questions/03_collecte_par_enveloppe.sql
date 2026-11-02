-- name: Collecte nette mensuelle par enveloppe (pic PER en décembre)
-- display: bar
select date_trunc('month', date_execution) as mois, enveloppe, sum(montant_signe_eur) as collecte_nette_eur
from analytics.finance.fct_mouvements
where date_execution >= '2022-01-01'
group by 1, 2
order by 1, 2
