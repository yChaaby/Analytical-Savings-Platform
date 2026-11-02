select
    code                                        as support,
    label                                       as libelle_support,
    asset_class                                 as classe_actifs,
    ongoing_charges_bps / 10000.0               as frais_courants
from {{ source('market', 'supports') }}
