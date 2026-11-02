with evenements as (

    select contrat_id, profil_initial as profil, ouvert_le as valide_du, 'souscription' as motif
    from {{ ref('stg_app__contracts') }}

    union all

    select contrat_id, nouveau_profil, effectif_le, motif
    from {{ ref('stg_app__mandate_changes') }}

)

select
    contrat_id,
    profil,
    motif,
    valide_du,
    lead(valide_du) over (partition by contrat_id order by valide_du)   as valide_au,
    lead(valide_du) over (partition by contrat_id order by valide_du) is null as est_actuel
from evenements
