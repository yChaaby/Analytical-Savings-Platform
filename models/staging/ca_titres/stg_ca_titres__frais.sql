select
    compte                                                                          as reference_partenaire,
    cast(date_trunc('month', {{ dbt.dateadd('month', -1, 'cast(date_prelevement as date)') }}) as date) as mois,
    sum(case when code_frais = 'FRAIS_TENUE_COMPTE'
             then {{ cents_to_eur('montant_centimes') }} else 0 end)                as frais_enveloppe_eur,
    sum(case when code_frais = 'FRAIS_MANDAT_GESTION'
             then {{ cents_to_eur('montant_centimes') }} else 0 end)                as frais_mandat_eur
from {{ source('ca_titres', 'frais') }}
where not _fivetran_deleted
group by 1, 2
