select
    id                                          as paiement_id,
    contract_id                                 as contrat_id,
    upper(promo_code)                           as code_promo,
    payment_type                                as type_paiement,
    cast(period_month as date)                  as mois_reference,
    cast(amount_eur as decimal(18, 2))          as montant_eur,
    cast(paid_at as timestamp)                  as paye_le,
    status                                      as statut
from {{ source('app', 'promo_payments') }}
where not _fivetran_deleted
