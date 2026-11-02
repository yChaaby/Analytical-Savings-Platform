with source as (
    select * from {{ source('app', 'contracts') }}
    where not _fivetran_deleted
)

select
    id                                          as contrat_id,
    client_id,
    lower(product_code)                         as produit,
    partner_code                                as partenaire,
    partner_contract_ref                        as reference_partenaire,
    initial_profile                             as profil_initial,
    management_mode                             as mode_gestion,
    upper(promo_code)                           as code_promo,
    cast(opened_at as timestamp)                as ouvert_le,
    cast(closed_at as timestamp)                as cloture_le,
    status                                      as statut
from source
