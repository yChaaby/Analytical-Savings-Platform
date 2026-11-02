{{ config(severity='warn') }}
with refs as (
    select reference_partenaire from {{ ref('stg_suravenir__valorisations') }}
    union select reference_partenaire from {{ ref('stg_spirica__valuations') }}
    union select reference_partenaire from {{ ref('stg_ca_titres__positions') }}
)
select r.reference_partenaire
from refs as r
left join {{ ref('stg_app__contracts') }} as c using (reference_partenaire)
where c.contrat_id is null
