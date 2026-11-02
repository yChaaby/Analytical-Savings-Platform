select
    profile                                     as profil,
    allocation_set                              as famille_allocation,
    support_code                                as support,
    target_weight                               as poids_cible
from {{ source('app', 'profile_allocations') }}
