-- name: Répartition de l'encours par profil de gestion (dernier jour)
-- display: bar
select 'P' || cast(profil as varchar) as profil, profil as ordre, sum(encours_eur) as encours_eur, count(distinct client_id) as clients
from analytics.finance.fct_encours_quotidien
where date_valorisation = (select max(date_valorisation) from analytics.finance.fct_encours_quotidien)
group by 1, 2
order by 2
