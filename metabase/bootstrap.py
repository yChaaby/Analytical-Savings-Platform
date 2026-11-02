"""Crée les questions et le dashboard Metabase à partir des fichiers de metabase/questions/.

Usage :
    python metabase/bootstrap.py --email moi@exemple.fr --password 'MotDePasse123!'
"""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
import time

import requests

HERE = pathlib.Path(__file__).resolve().parent
COLLECTION_NAME = "Pilotage épargne"

class Metabase:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.s = requests.Session()

    def call(self, method: str, path: str, **kw):
        r = self.s.request(method, f"{self.url}/api{path}", timeout=60, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code} : {r.text[:400]}")
        return r.json() if r.text else None

    def wait(self) -> None:
        for _ in range(60):
            try:
                if requests.get(f"{self.url}/api/health", timeout=5).json().get("status") == "ok":
                    return
            except Exception:
                pass
            time.sleep(5)
        sys.exit("Metabase ne répond pas sur /api/health. Est-il démarré ? (docker compose up -d)")

    def login_or_setup(self, email: str, password: str) -> None:
        props = self.call("GET", "/session/properties")
        token = props.get("setup-token")
        if token and not props.get("has-user-setup"):
            print("Initialisation de Metabase (compte administrateur)…")
            res = self.call("POST", "/setup", json={
                "token": token,
                "user": {"email": email, "password": password, "first_name": "Admin", "last_name": "Data",
                         "site_name": "Alto Analytics"},
                "prefs": {"site_name": "Alto Analytics", "allow_tracking": False},
            })
            session_id = res["id"]
        else:
            session_id = self.call("POST", "/session", json={"username": email, "password": password})["id"]
        self.s.headers["X-Metabase-Session"] = session_id

def snowflake_details() -> dict:
    """Paramètres de connexion Snowflake (authentification par clé RSA montée dans le conteneur)."""
    return {
        "account": os.environ.get("SNOWFLAKE_ACCOUNT", ""),
        "user": os.environ.get("METABASE_SNOWFLAKE_USER", "METABASE_SVC"),
        "warehouse": "REPORTING_WH",
        "db": "ANALYTICS",
        "role": "REPORTER",
        "use-password": False,
        "private-key-options": "local",
        "private-key-path": "/keys/metabase_svc_rsa_key.p8",
        "schema-filters-type": "inclusion",
        "schema-filters-patterns": "FINANCE,CLIENTS,SERVICE_CLIENT,REFERENTIEL",
    }

def find_or_create_database(mb: Metabase, name: str) -> int:
    dbs = mb.call("GET", "/database")
    dbs = dbs.get("data", dbs) if isinstance(dbs, dict) else dbs
    for db in dbs:
        if db["name"] == name:
            return db["id"]
    print(f"Base « {name} » absente : tentative de création automatique…")
    try:
        db = mb.call("POST", "/database", json={"engine": "snowflake", "name": name, "details": snowflake_details()})
        return db["id"]
    except RuntimeError as exc:
        sys.exit(
            f"Création automatique impossible ({exc}).\n"
            f"Ajoutez la base à la main : Admin > Bases de données > Ajouter > Snowflake, nommez-la « {name} » "
            "(voir README, section Metabase), puis relancez ce script."
        )

def parse_question(path: pathlib.Path) -> tuple[str, str, str]:
    sql = path.read_text(encoding="utf-8")
    name = re.search(r"^-- name: (.+)$", sql, re.M).group(1).strip()
    display = re.search(r"^-- display: (\w+)$", sql, re.M).group(1).strip()
    body = "\n".join(l for l in sql.splitlines() if not l.startswith("-- name:") and not l.startswith("-- display:"))
    return name, display, body.strip()

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:3000")
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--database-name", default="Snowflake ANALYTICS")
    args = ap.parse_args()

    mb = Metabase(args.url)
    mb.wait()
    mb.login_or_setup(args.email, args.password)
    db_id = find_or_create_database(mb, args.database_name)

    collections = mb.call("GET", "/collection")
    coll = next((c for c in collections if c.get("name") == COLLECTION_NAME), None) \
        or mb.call("POST", "/collection", json={"name": COLLECTION_NAME, "color": "#509EE3"})

    existing = {c["name"]: c for c in mb.call("GET", "/card") if c.get("collection_id") == coll["id"]}
    card_ids = []
    for path in sorted((HERE / "questions").glob("*.sql")):
        name, display, sql = parse_question(path)
        payload = {
            "name": name, "display": display, "collection_id": coll["id"], "visualization_settings": {},
            "dataset_query": {"type": "native", "native": {"query": sql}, "database": db_id},
        }
        if name in existing:
            card = mb.call("PUT", f"/card/{existing[name]['id']}", json=payload)
            print(f"  question mise à jour : {name}")
        else:
            card = mb.call("POST", "/card", json=payload)
            print(f"  question créée       : {name}")
        card_ids.append(card["id"])

    dash = mb.call("POST", "/dashboard", json={"name": "Pilotage épargne", "collection_id": coll["id"],
                                                "description": "Encours, collecte, revenus, offres, risques, service client"})
    dashcards = []
    for k, cid in enumerate(card_ids):
        dashcards.append({"id": -(k + 1), "card_id": cid, "row": (k // 2) * 6, "col": (k % 2) * 12,
                          "size_x": 12, "size_y": 6})
    mb.call("PUT", f"/dashboard/{dash['id']}", json={"dashcards": dashcards})
    print(f"\nDashboard prêt : {args.url}/dashboard/{dash['id']}")

if __name__ == "__main__":
    main()
