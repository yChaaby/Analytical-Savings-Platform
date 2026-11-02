select
    support_code                                as support,
    cast(price_date as date)                    as date_prix,
    cast(price as decimal(18, 4))               as prix
from {{ source('market', 'prix_supports') }}
