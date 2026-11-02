select
    contact_id,
    {{ normalize_email('email') }}              as email,
    cast(created_at as timestamp)               as cree_le,
    lead_source                                 as source_lead,
    newsletter_optin                            as optin_newsletter,
    lifecycle_stage                             as etape_cycle_de_vie
from {{ source('crm', 'contacts') }}
where not _fivetran_deleted
