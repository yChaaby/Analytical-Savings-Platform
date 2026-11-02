select
    num_contrat                                                         as reference_partenaire,
    cast(
        substr(periode, 1, 4) || '-' || substr(periode, 5, 2) || '-01'
    as date)                                                            as mois,
    cast(frais_gestion_contrat as decimal(18, 2))                       as frais_enveloppe_eur,
    cast(frais_mandat as decimal(18, 2))                                as frais_mandat_eur
from {{ source('suravenir', 'frais') }}
where not _fivetran_deleted
