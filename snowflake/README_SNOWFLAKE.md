# Mise en place Snowflake (essai gratuit 30 jours)

## 1. Créer le compte
Sur signup.snowflake.com : édition **Enterprise** (ou Standard), cloud et région au choix
(par exemple AWS, Europe (Paris) ou Frankfurt). Notez l'**identifiant de compte** au format
`ORGNAME-ACCOUNTNAME` (Snowsight → menu du compte en bas à gauche → *Connect a tool to Snowflake*).

## 2. Générer les paires de clés (sur votre machine)
Snowflake bloque progressivement les connexions par mot de passe seul : les outils (dbt, chargeur
Python, Metabase) utilisent donc une **paire de clés RSA**.

```bash
mkdir -p keys
# clé de l'utilisateur dbt / chargement
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/alto_svc_rsa_key.p8 -nocrypt
openssl rsa -in keys/alto_svc_rsa_key.p8 -pubout -out keys/alto_svc_rsa_key.pub
# clé de l'utilisateur Metabase
openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/metabase_svc_rsa_key.p8 -nocrypt
openssl rsa -in keys/metabase_svc_rsa_key.p8 -pubout -out keys/metabase_svc_rsa_key.pub
```
Le dossier `keys/` est ignoré par git : **ne jamais le committer**.

Pour coller une clé publique dans le script SQL, copiez son contenu **sans** les lignes
`-----BEGIN PUBLIC KEY-----` / `-----END PUBLIC KEY-----` et sans retours à la ligne :
```bash
grep -v "PUBLIC KEY" keys/alto_svc_rsa_key.pub | tr -d '\n'
```

## 3. Exécuter le script de mise en place
Snowsight → *Projects → Worksheets → + SQL Worksheet*, collez `snowflake/01_setup.sql`, remplacez
les deux `<COLLER_ICI_...>` puis *Run All*. Il crée : 3 entrepôts XS en arrêt automatique, un
plafond de crédits, les bases `RAW` et `ANALYTICS`, les rôles `LOADER` / `TRANSFORMER` / `REPORTER`
et deux utilisateurs de service.

## 4. Configurer l'environnement local
```bash
cp .env.example .env      # puis renseigner SNOWFLAKE_ACCOUNT
set -a; source .env; set +a
make snowflake-check      # teste la connexion
```

## Coûts
Chargement + `dbt build` complet ≈ quelques minutes d'entrepôt XS (≈ 1 crédit par heure d'activité).
Le moniteur de ressources suspend les entrepôts au-delà de 40 crédits par mois.
En fin d'essai : `snowflake/02_teardown.sql`.
