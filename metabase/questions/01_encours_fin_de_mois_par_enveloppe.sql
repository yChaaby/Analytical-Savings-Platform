-- name: Encours fin de mois par enveloppe
-- display: area
with fin_de_mois as (
    select date_trunc('month', date_valorisation) as mois, max(date_valorisation) as derniere_valo
    from analytics.finance.fct_encours_quotidien
    group by 1
)
select f.mois, e.enveloppe, sum(e.encours_eur) as encours_eur
from analytics.finance.fct_encours_quotidien as e
join fin_de_mois as f on e.date_valorisation = f.derniere_valo
group by 1, 2
order by 1, 2
