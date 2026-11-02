-include .env
export
export DBT_PROFILES_DIR := .
PYTHON ?= python3
SF := DBT_TARGET=snowflake

.PHONY: help install data build test docs metrics all \
        snowflake-check load-snowflake build-snowflake metrics-snowflake docs-snowflake snowflake-all \
        metabase-up metabase-bootstrap metabase-down clean

help:                ## Affiche cette aide
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:             ## Installe les dépendances Python
	pip install -r requirements.txt

snowflake-check:     ## Teste la connexion Snowflake
	$(PYTHON) ingestion/load_to_snowflake.py --check

load-snowflake:      ## Génère les données et les charge dans Snowflake (base RAW)
	$(PYTHON) ingestion/load_to_snowflake.py

build-snowflake:     ## dbt seed + run + snapshot + tests sur Snowflake
	$(SF) dbt build

metrics-snowflake:   ## Valide la semantic layer et lance le reporting mensuel sur Snowflake
	$(SF) mf validate-configs
	$(SF) mf query --saved-query reporting_mensuel_direction --order metric_time__month --decimals 0

docs-snowflake:      ## Génère et sert dbt Docs (lineage) sur http://localhost:8080
	$(SF) dbt docs generate && $(SF) dbt docs serve --port 8080

snowflake-all: load-snowflake build-snowflake metrics-snowflake   ## Pipeline complet sur Snowflake

data:                ## Génère les données brutes dans warehouse.duckdb
	$(PYTHON) ingestion/generate_sources.py --target duckdb --db warehouse.duckdb

build:               ## dbt build en local (DuckDB)
	dbt build

test:                ## Tests dbt uniquement (dont unit tests), en local
	dbt test

docs:                ## dbt Docs en local sur http://localhost:8080
	dbt docs generate && dbt docs serve --port 8080

metrics:             ## Semantic layer en local
	mf validate-configs
	mf query --saved-query reporting_mensuel_direction --order metric_time__month --decimals 0

all: data build metrics   ## Pipeline complet en local

metabase-up:         ## Démarre Metabase sur http://localhost:3000
	docker compose -f metabase/docker-compose.yml up -d

metabase-bootstrap:  ## Crée questions + dashboard (MB_EMAIL=... MB_PASSWORD=...)
	$(PYTHON) metabase/bootstrap.py --email "$(MB_EMAIL)" --password "$(MB_PASSWORD)"

metabase-down:       ## Arrête Metabase (les dashboards sont conservés)
	docker compose -f metabase/docker-compose.yml down

clean:               ## Supprime les artefacts locaux
	rm -rf target logs dbt_packages warehouse.duckdb data
