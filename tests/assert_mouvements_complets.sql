with source as (
    select count(*) as nb, sum(montant_eur) as total
    from {{ ref('stg_app__movements') }} where statut = 'executed'
),
fait as (
    select count(*) as nb, sum(montant_eur) as total from {{ ref('fct_mouvements') }}
)
select * from source cross join fait
where source.nb <> fait.nb or abs(source.total - fait.total) > 0.01
