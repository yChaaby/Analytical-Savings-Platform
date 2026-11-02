select
    mouvement_id,
    contrat_id,
    client_id,
    produit,
    enveloppe,
    partenaire,
    type_mouvement,
    sens,
    montant_eur,
    montant_signe_eur,
    date_execution,
    execute_le
from {{ ref('int_mouvements_executes') }}
