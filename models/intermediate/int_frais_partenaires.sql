with frais as (

    select * from {{ ref('stg_suravenir__frais') }}
    union all
    select * from {{ ref('stg_spirica__fees') }}
    union all
    select * from {{ ref('stg_ca_titres__frais') }}

)

select
    c.contrat_id,
    f.mois,
    f.frais_enveloppe_eur,
    f.frais_mandat_eur,
    f.frais_enveloppe_eur + f.frais_mandat_eur      as frais_totaux_eur
from frais as f
inner join {{ ref('stg_app__contracts') }} as c
    on f.reference_partenaire = c.reference_partenaire
