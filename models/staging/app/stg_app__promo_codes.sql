select
    upper(code)                                 as code_promo,
    offer_type                                  as type_offre,
    cast(valid_from as date)                    as valide_du,
    cast(valid_until as date)                   as valide_au,
    eligible_products                           as produits_eligibles,
    global_cap_eur                              as plafond_eur
from {{ source('app', 'promo_codes') }}
