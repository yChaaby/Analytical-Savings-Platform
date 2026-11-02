select
    extract(year from premier_contrat_le)                                       as cohorte,
    count(*)                                                                    as clients_entres,
    sum(case when statut_client = 'actif' then 1 else 0 end)                    as toujours_actifs,
    round(avg(case when statut_client = 'actif' then 1.0 else 0 end), 3)        as taux_retention,
    round(avg(case when statut_client = 'actif' then encours_actuel_eur end))   as encours_moyen_actifs_eur
from {{ ref('dim_clients') }}
where premier_contrat_le is not null and not est_mineur
group by 1
order by 1
