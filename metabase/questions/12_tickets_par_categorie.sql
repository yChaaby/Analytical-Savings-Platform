-- name: Tickets du service client par catégorie et par mois
-- display: bar
select date_trunc('month', date_creation) as mois, categorie, count(*) as tickets
from analytics.service_client.fct_tickets
group by 1, 2
order by 1, 2
