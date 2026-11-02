"""Génère les données brutes et les charge dans la base RAW de Snowflake.

Usage :
    python ingestion/load_to_snowflake.py
    python ingestion/load_to_snowflake.py --check
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas

sys.path.insert(0, os.path.dirname(__file__))
from generate_sources import Simulation

def connect():
    missing = [v for v in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PRIVATE_KEY_PATH") if not os.environ.get(v)]
    if missing:
        sys.exit(f"Variables manquantes : {missing}. Copier .env.example en .env puis `set -a; source .env; set +a`.")
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key_file=os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"],
        role=os.environ.get("SNOWFLAKE_LOADER_ROLE", "LOADER"),
        warehouse=os.environ.get("SNOWFLAKE_LOADER_WAREHOUSE", "LOADING_WH"),
        database=os.environ.get("SNOWFLAKE_RAW_DATABASE", "RAW"),
    )

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clients", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--check", action="store_true", help="teste la connexion et s'arrête")
    args = parser.parse_args()

    con = connect()
    cur = con.cursor()
    who = cur.execute("select current_user(), current_role(), current_warehouse(), current_database()").fetchone()
    print(f"Connecté : user={who[0]} role={who[1]} warehouse={who[2]} database={who[3]}")
    if args.check:
        return

    print(f"Génération des données ({args.clients} inscrits, seed={args.seed})…")
    tables = Simulation(args.clients, args.seed).run()

    database = os.environ.get("SNOWFLAKE_RAW_DATABASE", "RAW").upper()
    print(f"Chargement dans {database}…")
    for name, df in tables.items():
        schema, table = (part.upper() for part in name.split("."))
        cur.execute(f"create schema if not exists {database}.{schema}")
        start = time.time()
        ok, _, nrows, _ = write_pandas(
            con, df,
            table_name=table, database=database, schema=schema,
            auto_create_table=True, overwrite=True,
            quote_identifiers=False,
            use_logical_type=True,
        )
        print(f"  {database}.{schema}.{table:<24} {nrows:>10,} lignes  {'OK' if ok else 'ÉCHEC'}  ({time.time() - start:.0f}s)")
    con.close()
    print("Terminé. Étape suivante : make build-snowflake")

if __name__ == "__main__":
    main()
