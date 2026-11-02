-- name: Clients actifs par segment d'encours
-- display: pie
select segment_encours, count(*) as clients, sum(encours_actuel_eur) as encours_eur
from analytics.clients.dim_clients
where statut_client = 'actif'
group by 1
order by 3 desc
