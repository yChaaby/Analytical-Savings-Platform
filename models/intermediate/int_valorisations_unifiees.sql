with valorisations as (

    select 'SURAVENIR' as partenaire, * from {{ ref('stg_suravenir__valorisations') }}
    union all
    select 'SPIRICA'   as partenaire, * from {{ ref('stg_spirica__valuations') }}
    union all
    select 'CA_TITRES' as partenaire, * from {{ ref('stg_ca_titres__positions') }}

)

select
    c.contrat_id,
    v.partenaire,
    v.date_valorisation,
    v.encours_eur,
    v.encours_uc_eur,
    v.encours_fonds_euros_eur
from valorisations as v
inner join {{ ref('stg_app__contracts') }} as c
    on v.reference_partenaire = c.reference_partenaire
