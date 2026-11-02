-- name: Liste d'appel des conseillers (clients à risque, par priorité)
-- display: table
select priorite_appel, client_id, segment_encours, round(encours_actuel_eur, 0) as encours_eur,
       score_risque, niveau_risque, motifs
from analytics.clients.clients_a_contacter
order by priorite_appel
limit 50
