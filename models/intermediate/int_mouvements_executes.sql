select
    m.mouvement_id,
    m.contrat_id,
    c.client_id,
    c.produit,
    c.enveloppe,
    c.partenaire,
    m.type_mouvement,
    m.sens,
    m.montant_eur,
    case when m.sens = 'apport' then m.montant_eur else -m.montant_eur end   as montant_signe_eur,
    cast(m.execute_le as date)                                               as date_execution,
    m.execute_le
from {{ ref('stg_app__movements') }} as m
inner join {{ ref('int_contrats_enrichis') }} as c using (contrat_id)
where m.statut = 'executed'
