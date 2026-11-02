{{
    config(
        materialized='incremental',
        unique_key=['contrat_id', 'date_valorisation'],
        incremental_strategy='delete+insert',
        on_schema_change='append_new_columns'
    )
}}

with valorisations as (

    select * from {{ ref('int_valorisations_unifiees') }}
    {% if is_incremental() %}
    where date_valorisation >= (select {{ dbt.dateadd('day', -5, 'max(date_valorisation)') }} from {{ this }})
    {% endif %}

)

select
    v.contrat_id,
    c.client_id,
    c.produit,
    c.enveloppe,
    c.partenaire,
    p.profil,
    v.date_valorisation,
    v.encours_eur,
    v.encours_uc_eur,
    v.encours_fonds_euros_eur
from valorisations as v
inner join {{ ref('int_contrats_enrichis') }} as c using (contrat_id)
left join {{ ref('int_profil_contrat_historique') }} as p
    on p.contrat_id = v.contrat_id
   and v.date_valorisation >= cast(p.valide_du as date)
   and (p.valide_au is null or v.date_valorisation < cast(p.valide_au as date))
