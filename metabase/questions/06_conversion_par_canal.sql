-- name: Conversion inscription -> investissement par canal (12 derniers mois)
-- display: table
select
    canal_acquisition,
    count(*)                                                                        as inscrits,
    sum(case when statut_client in ('actif', 'parti') then 1 else 0 end)            as investis,
    round(avg(case when statut_client in ('actif', 'parti') then 1.0 else 0 end), 3) as taux_conversion,
    round(avg(case when statut_client = 'actif' then encours_actuel_eur end), 0)    as encours_moyen_actifs_eur
from analytics.clients.dim_clients
where not est_mineur
  and date_inscription > (select max(date_inscription) from analytics.clients.dim_clients) - 365
group by 1
order by investis desc
