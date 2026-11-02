select
    r.statut_rapprochement,
    r.code_promo,
    r.cle_periode                       as periode,
    r.contrat_id,
    c.client_id,
    cl.email,
    r.montant_du_eur,
    r.montant_paye_eur,
    r.ecart_eur,
    case
        when r.ecart_eur < 0 then 'a_payer'
        else 'a_recuperer_ou_annuler'
    end                                 as action
from {{ ref('finance_offres_rapprochement') }} as r
left join {{ ref('int_contrats_enrichis') }} as c using (contrat_id)
left join {{ ref('stg_app__clients') }} as cl on cl.client_id = c.client_id
where r.statut_rapprochement not in ('conforme', 'sans_objet')
