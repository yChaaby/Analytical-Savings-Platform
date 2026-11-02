with source as (
    select * from {{ source('app', 'clients') }}
    where not _fivetran_deleted
)

select
    id                                          as client_id,
    {{ normalize_email('email') }}              as email,
    first_name                                  as prenom,
    last_name                                   as nom,
    cast(birth_date as date)                    as date_naissance,
    postal_code                                 as code_postal,
    professional_category                       as categorie_socio_pro,
    annual_income_bracket                       as tranche_revenus,
    financial_assets_bracket                    as tranche_patrimoine_financier,
    investment_goal                             as objectif_placement,
    risk_questionnaire_score                    as score_questionnaire_risque,
    recommended_profile                         as profil_recommande,
    lower(acquisition_channel)                  as canal_acquisition,
    referrer_client_id                          as parrain_client_id,
    is_minor                                    as est_mineur,
    legal_representative_id                     as representant_legal_id,
    kyc_status                                  as statut_kyc,
    cast(kyc_validated_at as timestamp)         as kyc_valide_le,
    cast(created_at as timestamp)               as inscrit_le
from source
