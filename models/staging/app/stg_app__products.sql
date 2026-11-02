select
    code                                        as produit,
    label                                       as libelle_produit,
    wrapper                                     as enveloppe,
    partner_code                                as partenaire,
    min_initial_eur                             as versement_initial_min_eur,
    min_scheduled_eur                           as versement_programme_min_eur,
    mandate_fee_bps / 10000.0                   as taux_frais_mandat,
    wrapper_fee_bps / 10000.0                   as taux_frais_enveloppe,
    euro_fund_allowed                           as fonds_euros_possible,
    cast(open_from as date)                     as commercialise_du,
    cast(open_until as date)                    as commercialise_au
from {{ source('app', 'products') }}
