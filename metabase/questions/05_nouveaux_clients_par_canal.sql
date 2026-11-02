-- name: Nouveaux clients investis par canal d'acquisition
-- display: bar
select date_trunc('month', date_inscription) as mois, canal_acquisition, count(*) as nouveaux_clients
from analytics.clients.dim_clients
where statut_client in ('actif', 'parti') and not est_mineur and date_inscription >= '2022-01-01'
group by 1, 2
order by 1, 2
