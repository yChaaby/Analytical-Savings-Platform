select d.contrat_id, d.code_promo, sum(d.montant_du_eur) as total_du, max(p.plafond_eur) as plafond
from {{ ref('int_offres_droits') }} as d
inner join {{ ref('stg_app__promo_codes') }} as p using (code_promo)
group by 1, 2
having sum(d.montant_du_eur) > max(p.plafond_eur) + 0.01
