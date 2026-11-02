select
    policy_number                                                           as reference_partenaire,
    cast(month_start as date)                                               as mois,
    sum(case when fee_type = 'ADMIN' then amount_eur else 0 end)            as frais_enveloppe_eur,
    sum(case when fee_type = 'MANDATE' then amount_eur else 0 end)          as frais_mandat_eur
from {{ source('spirica', 'fees') }}
where not _fivetran_deleted
group by 1, 2
