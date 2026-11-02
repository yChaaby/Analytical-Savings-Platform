select
    d.*,
    case when d.date_echeance <= a.fin_mois_arrete then 'echu' else 'a_venir' end   as statut_echeance
from {{ ref('int_offres_droits') }} as d
cross join {{ ref('int_date_arrete') }} as a
