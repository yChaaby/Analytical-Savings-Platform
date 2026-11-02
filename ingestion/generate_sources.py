"""Génère les données brutes synthétiques et les écrit dans DuckDB ou en fichiers Parquet.

Usage :
    python ingestion/generate_sources.py --target duckdb --db warehouse.duckdb
    python ingestion/generate_sources.py --target parquet --out data/raw
"""

from __future__ import annotations

import argparse
import json
import pathlib
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

try:
    from . import referentiel as R
except ImportError:
    import referentiel as R

def _pick(rng: np.random.Generator, d: dict[str, float], size=None):
    keys = list(d)
    p = np.array(list(d.values()), dtype=float)
    return rng.choice(keys, size=size, p=p / p.sum())

def _messy_email(email: str, rng: np.random.Generator) -> str:
    r = rng.random()
    if r < 0.12:
        return email.upper()
    if r < 0.20:
        return f" {email}  "
    if r < 0.28:
        return email.capitalize()
    return email

class Simulation:
    def __init__(self, n_clients: int = 6000, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.fake = Faker("fr_FR")
        Faker.seed(seed)
        self.n_clients = n_clients
        self.days = pd.date_range(R.START, R.END, freq="D")
        self.n_days = len(self.days)
        self.business = (self.days.weekday < 5)
        self.month_idx = (self.days.year - R.START.year) * 12 + self.days.month - 1
        self.n_months = int(self.month_idx.max()) + 1
        self.months = pd.date_range(R.START, periods=self.n_months, freq="MS")

    def simuler_marche(self) -> None:
        rng = self.rng
        supports = list(R.SUPPORTS)
        n_s = len(supports)
        years = self.days.year.to_numpy()
        market = rng.normal(0, 1, self.n_days)
        log_r = np.zeros((n_s, self.n_days))
        for i, s in enumerate(supports):
            classe = R.SUPPORTS[s][1]
            vol = R.VOLATILITES[s]
            if classe == "actions":
                noise = 0.8 * market + 0.6 * rng.normal(0, 1, self.n_days)
            elif classe == "obligations":
                noise = 0.3 * market + 0.95 * rng.normal(0, 1, self.n_days)
            else:
                noise = rng.normal(0, 1, self.n_days)
            noise = noise * vol / np.sqrt(252)
            for k, y in enumerate(range(R.START.year, R.END.year + 1)):
                if classe == "fonds_euros":
                    mask = years == y
                    days_in_year = 366 if y % 4 == 0 else 365
                    log_r[i, mask] = np.log1p(R.RENDEMENTS_ANNUELS[s][k]) / days_in_year
                    continue
                mask = (years == y) & self.business
                seg = noise[mask]
                seg = seg - seg.mean()
                log_r[i, mask] = seg + np.log1p(R.RENDEMENTS_ANNUELS[s][k]) / mask.sum()
        self.support_codes = supports
        self.support_ret = np.expm1(log_r)
        self.support_price = 100 * np.exp(np.cumsum(log_r, axis=1))

        self.port_ret = np.zeros((2, 11, self.n_days))
        self.uc_share = np.ones((2, 11))
        for fe in (0, 1):
            for p in range(1, 11):
                alloc = R.allocation(p, bool(fe))
                w = np.array([alloc.get(s, 0.0) for s in supports])
                self.port_ret[fe, p] = w @ self.support_ret
                self.uc_share[fe, p] = 1 - alloc.get("FONDS_EUROS", 0.0)

    def simuler_clients(self) -> None:
        rng, fake = self.rng, self.fake
        n = self.n_clients
        n_hist = int(n * 0.25)
        n_new = n - n_hist

        t = np.arange(self.n_days)
        w = np.exp(0.22 * t / 365)
        saison = {1: 1.35, 2: 1.1, 3: 1.1, 4: 1.0, 5: 0.95, 6: 0.9, 7: 0.75, 8: 0.6, 9: 1.05, 10: 1.0, 11: 1.0, 12: 1.2}
        w *= np.array([saison[m] for m in self.days.month])
        w *= np.where(self.business, 1.0, 0.7)
        for promo in R.PROMOS:
            w *= np.where((self.days.date >= promo["du"]) & (self.days.date <= promo["au"]), 1.45, 1.0)
        new_days = np.sort(rng.choice(self.n_days, size=n_new, p=w / w.sum()))
        hist_dates = pd.to_datetime(rng.uniform(
            pd.Timestamp("2016-01-01").value, pd.Timestamp("2021-12-31").value, n_hist)).sort_values().floor("s")

        signups = list(hist_dates) + [self.days[d] + timedelta(seconds=int(rng.integers(6 * 3600, 23 * 3600)))
                                      for d in new_days]
        rows = []
        for i, signup in enumerate(signups):
            signup = pd.Timestamp(signup)
            age = int(np.clip(rng.normal(40, 11), 18, 78))
            first, last = fake.first_name(), fake.last_name()
            email = f"{first}.{last}.{i}@{fake.free_email_domain()}".lower()
            email = email.replace(" ", "").replace("'", "").encode("ascii", "ignore").decode()
            csp = "retraite" if age >= 64 else _pick(rng, {k: v for k, v in R.CSP.items() if k != "retraite"})
            score = np.clip(rng.normal(7.5 - (age - 40) * 0.06, 1.6), 1, 10)
            profil_reco = int(round(score))
            canal = _pick(rng, R.CANAUX)
            kyc_r = rng.random()
            recent = (pd.Timestamp(R.END) - signup).days < 15
            kyc = "pending" if recent and kyc_r < 0.6 else ("rejected" if kyc_r < 0.03 else
                                                            "pending" if kyc_r < 0.05 else "validated")
            rows.append(dict(
                id=100_000 + i,
                email=_messy_email(email, rng),
                first_name=first, last_name=last,
                birth_date=(signup - pd.Timedelta(days=int(age * 365.25 + rng.integers(0, 365)))).date(),
                postal_code=fake.postcode(),
                professional_category=csp,
                annual_income_bracket=_pick(rng, {"<30k": 0.15, "30-50k": 0.30, "50-80k": 0.28, "80-150k": 0.19, ">150k": 0.08}),
                financial_assets_bracket=_pick(rng, {"<20k": 0.22, "20-100k": 0.38, "100-300k": 0.26, "300k-1M": 0.11, ">1M": 0.03}),
                investment_goal=_pick(rng, R.OBJECTIFS),
                risk_questionnaire_score=round(float(score), 1),
                recommended_profile=profil_reco,
                acquisition_channel=canal.upper() if rng.random() < 0.05 else canal,
                referrer_client_id=None,
                is_minor=False,
                legal_representative_id=None,
                kyc_status=kyc,
                kyc_validated_at=(signup + timedelta(hours=int(rng.integers(1, 120)))) if kyc == "validated" else None,
                created_at=signup.to_pydatetime(),
                _age=age,
            ))
        self.clients = pd.DataFrame(rows)
        parr = self.clients.index[self.clients["acquisition_channel"].str.lower() == "parrainage"]
        for idx in parr:
            if idx > 10:
                self.clients.loc[idx, "referrer_client_id"] = int(self.clients.loc[rng.integers(0, idx), "id"])
        self.clients["referrer_client_id"] = self.clients["referrer_client_id"].astype("Int64")
        self.clients["legal_representative_id"] = self.clients["legal_representative_id"].astype("Int64")

    def _montant_initial(self, produit: str, promo_active: dict | None) -> float:
        rng = self.rng
        if rng.random() < 0.55:
            amount = float(np.round(rng.lognormal(np.log(4000), 1.0), -2))
        else:
            amount = float(rng.choice([1000, 2000, 3000, 5000, 10000, 15000, 20000, 25000, 30000, 50000, 75000, 100000, 150000],
                                      p=[.14, .09, .07, .15, .15, .06, .06, .09, .04, .08, .03, .03, .01]))
        amount = max(amount, R.PRODUITS[produit]["min_initial"])
        if promo_active:
            for seuil, _ in promo_active["paliers"]:
                if 0.6 * seuil <= amount < seuil and rng.random() < 0.45:
                    amount = float(seuil)
        return amount

    def _choisir_produit(self, objectif: str, jour: date, age: int, exclus: set[str]) -> str | None:
        dispo = {}
        for code, p in R.PRODUITS.items():
            if code == "assurance_vie_kids" or code in exclus:
                continue
            if p["ouvert_du"] <= jour and (p["ouvert_au"] is None or jour <= p["ouvert_au"]):
                poids = p["part"]
                if code.startswith("per"):
                    poids *= 3.0 if objectif == "preparer_retraite" else 0.6
                    poids *= 0.3 if age > 62 else 1.0
                if code == "pea" and objectif == "faire_fructifier":
                    poids *= 1.6
                dispo[code] = poids
        return _pick(self.rng, dispo) if dispo else None

    def simuler_contrats(self) -> None:
        rng = self.rng
        promos_by_day = {}
        contrats, kids_clients = [], []
        cid = 3_000_000
        next_client_id = int(self.clients["id"].max()) + 1

        def promo_pour(jour: date, produit: str) -> dict | None:
            for pr in R.PROMOS:
                if pr["du"] <= jour <= pr["au"] and produit in pr["produits"]:
                    return pr
            return None

        def nouveau_contrat(client_id, produit, opened, profil, montant_hint=None, historique=False):
            nonlocal cid
            jour = opened.date()
            promo = None if historique else promo_pour(jour, produit)
            montant = self._montant_initial(produit, promo)
            transfert = produit.startswith("per") and rng.random() < 0.35
            if produit == "pea" and rng.random() < 0.08:
                transfert = True
            if transfert:
                montant = float(np.round(rng.lognormal(np.log(18000), 0.9), -1))
            code_promo = None
            if promo and montant >= promo["paliers"][0][0] and rng.random() < 0.7:
                code_promo = promo["code"]
            p = R.PRODUITS[produit]
            profil = 10 if produit == "pea" else int(np.clip(profil, min(p["profils"]), max(p["profils"])))
            ref = {"SURAVENIR": f"SV{cid:08d}", "SPIRICA": f"SP-{cid}", "CA_TITRES": f"CAT{cid:09d}"}[p["partenaire"]]
            contrats.append(dict(
                id=cid, client_id=int(client_id),
                product_code=produit.upper() if rng.random() < 0.15 else produit,
                partner_code=p["partenaire"], partner_contract_ref=ref,
                initial_profile=profil,
                management_mode=("horizon" if produit == "per_assurantiel" and rng.random() < 0.4 else "sous_mandat"),
                opened_at=opened.to_pydatetime(), closed_at=None, status="open",
                promo_code=code_promo,
                _initial_amount=montant, _transfer=transfert, _historique=historique,
            ))
            cid += 1
            return cid - 1

        validated = self.clients[self.clients["kyc_status"] == "validated"]
        for _, c in validated.iterrows():
            created = pd.Timestamp(c["created_at"])
            historique = created < pd.Timestamp(R.START)
            if not historique and rng.random() > 0.72:
                continue
            opened = pd.Timestamp(c["kyc_validated_at"]).floor("s") + timedelta(days=int(rng.geometric(0.15)) - 1, hours=int(rng.integers(0, 8)))
            if opened.date() > R.END:
                continue
            profil = c["recommended_profile"] + (int(rng.choice([-1, 0, 0, 0, 1])))
            exclus: set[str] = set()
            produit = self._choisir_produit(c["investment_goal"], opened.date(), c["_age"], exclus)
            if produit is None:
                continue
            nouveau_contrat(c["id"], produit, opened, profil, historique=opened < pd.Timestamp(R.START))
            exclus.add(produit)

            for _ in range(rng.poisson(0.4)):
                later = opened + timedelta(days=int(rng.integers(30, 1200)))
                if later.date() > R.END:
                    continue
                prod2 = self._choisir_produit(c["investment_goal"], later.date(), c["_age"], exclus)
                if prod2:
                    nouveau_contrat(c["id"], prod2, later, profil, historique=later < pd.Timestamp(R.START))
                    exclus.add(prod2)

            if 28 <= c["_age"] <= 50 and rng.random() < 0.10:
                kid_open = opened + timedelta(days=int(rng.integers(0, 900)))
                if kid_open.date() <= R.END:
                    kid_age = int(rng.integers(0, 15))
                    kids_clients.append(dict(
                        id=next_client_id, email=None, first_name=self.fake.first_name(), last_name=c["last_name"],
                        birth_date=(kid_open - pd.Timedelta(days=int(kid_age * 365.25 + rng.integers(0, 365)))).date(),
                        postal_code=c["postal_code"], professional_category=None, annual_income_bracket=None,
                        financial_assets_bracket=None, investment_goal="financer_etudes_enfants",
                        risk_questionnaire_score=None, recommended_profile=None, acquisition_channel="direct",
                        referrer_client_id=None, is_minor=True, legal_representative_id=int(c["id"]),
                        kyc_status="validated", kyc_validated_at=kid_open.to_pydatetime(),
                        created_at=kid_open.to_pydatetime(), _age=kid_age))
                    nouveau_contrat(next_client_id, "assurance_vie_kids", kid_open, 8,
                                    historique=kid_open < pd.Timestamp(R.START))
                    next_client_id += 1

        if kids_clients:
            kids = pd.DataFrame(kids_clients)
            self.clients = pd.concat([self.clients, kids], ignore_index=True)
            self.clients["referrer_client_id"] = self.clients["referrer_client_id"].astype("Int64")
            self.clients["legal_representative_id"] = self.clients["legal_representative_id"].astype("Int64")
        self.contrats = pd.DataFrame(contrats).sort_values("opened_at").reset_index(drop=True)

    def simuler_vie_des_contrats(self) -> None:
        rng = self.rng
        ct = self.contrats
        n_ct = len(ct)
        n_days = self.n_days
        produit = ct["product_code"].str.lower().to_numpy()
        fe = np.array([1 if R.PRODUITS[p]["fonds_euros"] else 0 for p in produit])
        mandat_rate = np.array([R.PRODUITS[p]["frais_mandat_bps"] for p in produit]) / 1e4 / 365
        env_rate = np.array([R.PRODUITS[p]["frais_enveloppe_bps"] for p in produit]) / 1e4 / 365
        opened = pd.to_datetime(ct["opened_at"])
        open_idx = ((opened.dt.normalize() - pd.Timestamp(R.START)).dt.days).to_numpy()
        hist = open_idx < 0
        open_idx_c = np.clip(open_idx, 0, n_days - 1)
        client_age = ct["client_id"].map(self.clients.set_index("id")["_age"]).to_numpy()

        flows = np.zeros((n_days, n_ct))
        mvts: list[dict] = []
        mid = [50_000_000]

        def mvt(i, when: pd.Timestamp, kind, amount, status="executed", exec_delay_days=2):
            requested = when
            executed = (when + timedelta(days=exec_delay_days)).replace(hour=10, minute=0) if status == "executed" else None
            if executed is not None and executed > pd.Timestamp(R.END) + timedelta(hours=23):
                status, executed = "pending", None
            mvts.append(dict(id=mid[0], contract_id=int(ct.at[i, "id"]), movement_type=kind,
                             amount_cents=str(int(round(amount * 100))), status=status,
                             requested_at=requested.to_pydatetime(),
                             executed_at=executed.to_pydatetime() if executed is not None else None))
            mid[0] += 1
            if status == "executed" and executed is not None:
                d = (executed.normalize() - pd.Timestamp(R.START)).days
                if 0 <= d < n_days:
                    flows[d, i] += amount if kind.startswith(("versement", "transfert")) else 0.0
            return executed

        nav = np.zeros(n_ct)
        programme = np.zeros(n_ct, dtype=bool)
        for i in range(n_ct):
            p = produit[i]
            amount = float(ct.at[i, "_initial_amount"])
            kind = "transfert_entrant" if ct.at[i, "_transfer"] else "versement_initial"
            op = pd.Timestamp(ct.at[i, "opened_at"])
            if hist[i]:

                mvt(i, op, kind, amount)
                years = (pd.Timestamp(R.START) - op).days / 365
                nav[i] = amount * (1 + 0.05) ** years * rng.uniform(1.0, 2.2)
            else:
                mvt(i, op, kind, amount)

            prob_prog = {"per_bancaire": 0.6, "per_assurantiel": 0.6, "assurance_vie_kids": 0.75}.get(p, 0.48)
            if rng.random() < prob_prog:
                programme[i] = True
                m_min = R.PRODUITS[p]["min_programme"]
                monthly = float(max(m_min, rng.choice([50, 100, 150, 200, 250, 300, 500, 1000], p=[.16, .25, .14, .14, .06, .12, .1, .03])))
                day_of_month = int(rng.choice([5, 10, 15, 20]))
                start = max(op, pd.Timestamp(R.START)) + pd.DateOffset(months=1)
                stop = pd.Timestamp(R.END) if rng.random() > 0.25 else start + timedelta(days=int(rng.integers(90, 1400)))
                for m in pd.date_range(start.replace(day=1), min(stop, pd.Timestamp(R.END)), freq="MS"):
                    when = m.replace(day=day_of_month) + timedelta(hours=6)
                    if when > pd.Timestamp(R.END):
                        break
                    status = "executed" if rng.random() > 0.02 else "rejected"
                    mvt(i, when, "versement_programme", monthly, status)

            first = max(op, pd.Timestamp(R.START))
            span = max((pd.Timestamp(R.END) - first).days, 0)
            for _ in range(rng.poisson(0.7 * span / 365)):
                when = first + timedelta(days=int(rng.integers(1, max(span, 2))), hours=int(rng.integers(8, 22)))
                mvt(i, when, "versement_libre", float(np.round(rng.lognormal(np.log(1800), 0.9), -1)))
            if p.startswith("per"):
                for y in range(first.year, R.END.year + 1):
                    if rng.random() < 0.28 and date(y, 12, 1) > first.date() and date(y, 12, 20) <= R.END:
                        when = pd.Timestamp(date(y, 12, int(rng.integers(1, 21)))) + timedelta(hours=int(rng.integers(8, 22)))
                        mvt(i, when, "versement_libre", float(np.round(rng.lognormal(np.log(3500), 0.8), -1)))

        profil = ct["initial_profile"].to_numpy().astype(int).copy()
        events: dict[int, list[tuple[int, int, str]]] = {}
        changes = []
        chg_id = 900_000
        for i in range(n_ct):
            p = produit[i]
            if p == "pea":
                continue
            allowed = R.PRODUITS[p]["profils"]
            cur = profil[i]
            start = max(open_idx[i], 0) + 30
            t = start
            while True:
                t += int(rng.exponential(365 / 0.08))
                if t >= n_days:
                    break
                dd = self.days[t]
                drawdown = date(2022, 3, 1) <= dd.date() <= date(2022, 10, 31)
                step = rng.choice([-1, 1], p=[0.75, 0.25] if drawdown else [0.4, 0.6])
                new = int(np.clip(cur + step, min(allowed), max(allowed)))
                if new != cur:
                    events.setdefault(t, []).append((i, new, "demande_client" if rng.random() < 0.7 else "mise_a_jour_questionnaire"))
                    cur = new
            if ct.at[i, "management_mode"] == "horizon":
                age0 = client_age[i]
                for y in range(R.START.year + 1, R.END.year + 1):
                    if age0 + (y - R.START.year) >= 50:
                        t = (pd.Timestamp(date(y, 1, 2)) - pd.Timestamp(R.START)).days
                        if t > open_idx[i]:
                            events.setdefault(t, []).append((i, -1, "desensibilisation_horizon"))

        n_m = self.n_months
        fees_mandat = np.zeros((n_m, n_ct))
        fees_env = np.zeros((n_m, n_ct))
        nav_hist = np.zeros((n_days, n_ct), dtype=np.float64)
        uc_hist = np.zeros((n_days, n_ct), dtype=np.float32)
        closed_at = np.full(n_ct, -1)
        alive_since = np.where(hist, 0, open_idx)
        base_churn = np.array([{"per_bancaire": 0.004, "per_assurantiel": 0.004, "assurance_vie_kids": 0.012,
                                "pea": 0.04, "cto": 0.05}.get(p, 0.035) for p in produit]) / 365
        base_partial = np.array([{"per_bancaire": 0.004, "per_assurantiel": 0.004, "assurance_vie_kids": 0.01,
                                  "pea": 0.035, "cto": 0.06}.get(p, 0.045) for p in produit]) / 365
        base_churn = base_churn * np.where(programme, 0.6, 1.3)

        for t in range(n_days):
            for (i, new, reason) in events.get(t, []):
                if closed_at[i] >= 0:
                    continue
                old = profil[i]
                if new == -1:
                    new = max(3, old - 1)
                if new == old:
                    continue
                profil[i] = new
                changes.append(dict(id=chg_id, contract_id=int(ct.at[i, "id"]), previous_profile=int(old), new_profile=int(new),
                                    reason=reason, effective_at=(self.days[t] + timedelta(hours=9)).to_pydatetime()))
                chg_id += 1
            alive = (t >= alive_since) & (closed_at < 0)
            r = self.port_ret[fe, profil, t]
            cur = nav * (1 + r)
            uc = self.uc_share[fe, profil]
            f_m = cur * uc * mandat_rate * alive
            f_e = cur * uc * env_rate * alive
            cur = cur - f_m - f_e + flows[t]
            fees_mandat[self.month_idx[t]] += f_m
            fees_env[self.month_idx[t]] += f_e
            if self.business[t]:
                dd = self.days[t].date()
                stress = 1.8 if date(2022, 2, 15) <= dd <= date(2022, 10, 31) else 1.0
                tenure_factor = np.where(t - alive_since < 365, 1.4, 1.0)
                eligible = alive & (cur > 0) & (t > alive_since + 45)
                churn = eligible & (rng.random(n_ct) < base_churn * 7 / 5 * stress * tenure_factor)
                for i in np.where(churn)[0]:
                    mvt(i, self.days[t] + timedelta(hours=11), "rachat_total", float(round(cur[i], 2)), exec_delay_days=0)
                    closed_at[i] = t
                    cur[i] = 0.0
                partial = eligible & ~churn & (rng.random(n_ct) < base_partial * 7 / 5 * stress)
                for i in np.where(partial)[0]:
                    amt = float(np.round(cur[i] * rng.uniform(0.05, 0.4), 2))
                    mvt(i, self.days[t] + timedelta(hours=11), "rachat_partiel", amt, exec_delay_days=0)
                    cur[i] -= amt
            cur[closed_at >= 0] = np.where(closed_at[closed_at >= 0] == t, 0.0, 0.0)
            nav = np.maximum(cur, 0)
            nav_hist[t] = nav
            uc_hist[t] = uc

        mv = pd.DataFrame(mvts)
        close_map = {int(ct.at[i, "id"]): self.days[closed_at[i]] for i in np.where(closed_at >= 0)[0]}
        ct_close = mv["contract_id"].map(close_map)
        after_close = ct_close.notna() & (pd.to_datetime(mv["requested_at"]) > ct_close + pd.Timedelta(hours=12)) \
            & mv["movement_type"].str.startswith("versement")
        self.mouvements = mv[~after_close].reset_index(drop=True)
        for i, d in close_map.items():
            idx = ct.index[ct["id"] == i][0]
            ct.at[idx, "closed_at"] = (d + timedelta(hours=18)).to_pydatetime()
            ct.at[idx, "status"] = "closed"
        self.contrats = ct
        self.changements_profil = pd.DataFrame(changes)
        self.nav_hist, self.uc_hist = nav_hist, uc_hist
        self.fees_mandat, self.fees_env = fees_mandat, fees_env

    def fichiers_partenaires(self) -> dict[str, pd.DataFrame]:
        rng = self.rng
        ct = self.contrats
        out = {}
        rows_t, rows_i = np.where((self.nav_hist > 0.005) & self.business[:, None])
        nav = self.nav_hist[rows_t, rows_i]
        uc = self.uc_hist[rows_t, rows_i]
        part = ct["partner_code"].to_numpy()[rows_i]
        ref = ct["partner_contract_ref"].to_numpy()[rows_i]
        dates = self.days[rows_t].date

        m = part == "SURAVENIR"
        out["raw_suravenir.valorisations"] = pd.DataFrame({
            "num_contrat": ref[m], "date_valeur": dates[m],
            "montant_epargne": np.round(nav[m], 2),
            "montant_uc": np.round(nav[m] * uc[m], 2),
            "montant_fonds_euros": np.round(nav[m] * (1 - uc[m]), 2),
        })
        m = part == "SPIRICA"
        out["raw_spirica.valuations"] = pd.DataFrame({
            "policy_number": ref[m], "nav_date": [d.isoformat() for d in dates[m]],
            "total_value_eur": np.round(nav[m], 2),
        })
        m = part == "CA_TITRES"
        cash = np.round(nav[m] * 0.01, 2)
        out["raw_ca_titres.positions"] = pd.DataFrame({
            "compte": ref[m], "date_position": dates[m],
            "valorisation_titres": np.round(nav[m], 2) - cash, "solde_especes": cash,
        })

        mi, ci = np.where((self.fees_mandat + self.fees_env) > 0.005)
        f_m = np.round(self.fees_mandat[mi, ci], 2)
        f_e = np.round(self.fees_env[mi, ci], 2)
        wrong = rng.random(len(mi)) < 0.004
        f_m = np.where(wrong, np.round(f_m * 0.80 / 0.70, 2), f_m)
        keep = rng.random(len(mi)) > 0.002
        mi, ci, f_m, f_e = mi[keep], ci[keep], f_m[keep], f_e[keep]
        mois = self.months[mi]
        part = ct["partner_code"].to_numpy()[ci]
        ref = ct["partner_contract_ref"].to_numpy()[ci]
        self.frais_reportes = pd.DataFrame({"contract_id": ct["id"].to_numpy()[ci], "mois": mois, "frais": f_m + f_e})

        m = part == "SURAVENIR"
        out["raw_suravenir.frais"] = pd.DataFrame({
            "num_contrat": ref[m], "periode": mois[m].strftime("%Y%m"),
            "frais_gestion_contrat": f_e[m], "frais_mandat": f_m[m],
        })
        m = part == "SPIRICA"
        sp = pd.DataFrame({"policy_number": ref[m], "month_start": mois[m].date, "ADMIN": f_e[m], "MANDATE": f_m[m]})
        out["raw_spirica.fees"] = sp.melt(id_vars=["policy_number", "month_start"], var_name="fee_type", value_name="amount_eur")
        m = part == "CA_TITRES"
        prelev = (mois[m] + pd.DateOffset(months=1) + pd.Timedelta(days=4)).date
        ca = pd.DataFrame({"compte": ref[m], "date_prelevement": prelev,
                           "FRAIS_TENUE_COMPTE": f_e[m], "FRAIS_MANDAT_GESTION": f_m[m]})
        ca = ca.melt(id_vars=["compte", "date_prelevement"], var_name="code_frais", value_name="montant")
        ca["montant_centimes"] = (ca.pop("montant") * 100).round().astype("int64").astype(str)
        out["raw_ca_titres.frais"] = ca
        return out

    def paiements_offres(self) -> pd.DataFrame:
        """Paiements des offres saisis par l'équipe opérations, avec des erreurs volontaires."""
        rng = self.rng
        ct = self.contrats[self.contrats["promo_code"].notna()]
        promos = {p["code"]: p for p in R.PROMOS}
        mv = self.mouvements[self.mouvements["status"] == "executed"].copy()
        mv["amount"] = mv["amount_cents"].astype(int) / 100
        mv["signe"] = np.where(mv["movement_type"].str.startswith("rachat"), -1, 1)
        mv["mois"] = pd.to_datetime(mv["executed_at"]).dt.to_period("M").dt.to_timestamp()
        fees = self.frais_reportes.set_index(["contract_id", "mois"])["frais"]
        out, pid = [], 7_000_000
        end = pd.Timestamp(R.END)
        for _, c in ct.iterrows():
            promo = promos[c["promo_code"]]
            initial = float(c["_initial_amount"])
            tier = [p for p in promo["paliers"] if initial >= p[0]][-1]
            seuil, valeur = tier
            m_mv = mv[mv["contract_id"] == c["id"]]
            apports = m_mv.groupby("mois").apply(lambda g: (g["amount"] * g["signe"]).sum(), include_groups=False).cumsum()
            closed = pd.Timestamp(c["closed_at"]) if c["closed_at"] is not None and not pd.isna(c["closed_at"]) else None
            opened = pd.Timestamp(c["opened_at"])

            def condition_ok(month_start: pd.Timestamp) -> bool:
                month_end = month_start + pd.offsets.MonthEnd(0)
                if closed is not None and closed <= month_end + pd.Timedelta(hours=23):
                    return False
                s = apports[apports.index <= month_start]
                return (s.iloc[-1] if len(s) else 0) >= seuil - 0.01

            if promo["type"] == "prime":
                m3 = (opened + pd.DateOffset(months=3)).to_period("M").to_timestamp()
                paid = m3 + pd.offsets.MonthEnd(0)
                ok = condition_ok(m3)
                if paid <= end and (ok or rng.random() < 0.05):
                    out.append(dict(id=pid, contract_id=int(c["id"]), promo_code=promo["code"], payment_type="prime",
                                    period_month=None, amount_eur=float(valeur), paid_at=paid.to_pydatetime(), status="paid"))
                    pid += 1
                continue

            first = (opened + pd.offsets.MonthBegin(1)).normalize() if opened.day != 1 else opened.normalize()
            cumul, rompu = 0.0, False
            for k in range(int(valeur)):
                month = first + pd.DateOffset(months=k)
                paid = month + pd.DateOffset(months=1) + pd.offsets.MonthEnd(0)
                if paid > end:
                    break
                if not condition_ok(month):
                    rompu = True
                if rompu and rng.random() > 0.15:
                    break
                f = float(fees.get((c["id"], month), 0.0))
                amount = round(min(f, promo["plafond"] - cumul), 2)
                if amount <= 0:
                    if cumul >= promo["plafond"] - 0.005:
                        break
                    continue
                cumul += amount
                if rng.random() < 0.02:
                    continue
                n = 2 if rng.random() < 0.01 else 1
                for _ in range(n):
                    out.append(dict(id=pid, contract_id=int(c["id"]), promo_code=promo["code"],
                                    payment_type="remboursement_frais", period_month=month.date(),
                                    amount_eur=amount, paid_at=paid.to_pydatetime(), status="paid"))
                    pid += 1
        return pd.DataFrame(out)

    def crm_et_support(self) -> dict[str, pd.DataFrame]:
        rng, fake = self.rng, self.fake
        cl = self.clients[self.clients["email"].notna()]
        contacts = pd.DataFrame({
            "contact_id": (cl["id"] * 3 + 7).astype(str),
            "email": cl["email"].str.strip().str.lower(),
            "created_at": pd.to_datetime(cl["created_at"]) - pd.to_timedelta(rng.integers(0, 60, len(cl)), unit="D"),
            "lead_source": cl["acquisition_channel"].str.lower(),
            "newsletter_optin": rng.random(len(cl)) < 0.62,
            "lifecycle_stage": "customer",
        })
        n_leads = int(len(cl) * 0.6)
        leads = pd.DataFrame({
            "contact_id": [f"L{i:07d}" for i in range(n_leads)],
            "email": [f"lead{i}.{fake.user_name()}@{fake.free_email_domain()}" for i in range(n_leads)],
            "created_at": pd.to_datetime(rng.uniform(pd.Timestamp(R.START).value, pd.Timestamp(R.END).value, n_leads)),
            "lead_source": _pick(rng, R.CANAUX, n_leads),
            "newsletter_optin": rng.random(n_leads) < 0.8,
            "lifecycle_stage": rng.choice(["subscriber", "lead", "marketing_qualified_lead"], n_leads, p=[.5, .35, .15]),
        })
        crm = pd.concat([contacts, leads], ignore_index=True)

        tickets = []
        clients_actifs = cl[cl["kyc_status"] == "validated"].reset_index(drop=True)
        n_t = int(len(clients_actifs) * 0.9)
        for k in range(n_t):
            c = clients_actifs.iloc[int(rng.integers(0, len(clients_actifs)))]
            created = max(pd.Timestamp(c["created_at"]), pd.Timestamp(R.START)) + timedelta(
                days=int(rng.integers(0, 1200)), hours=int(rng.integers(8, 20)))
            if created > pd.Timestamp(R.END):
                continue
            cat = _pick(rng, R.CATEGORIES_TICKETS)
            if created.month in (3, 4, 5) and rng.random() < 0.3:
                cat = "fiscalite"
            if date(2022, 3, 1) <= created.date() <= date(2022, 10, 31) and rng.random() < 0.25:
                cat = "performance"
            status = rng.choice(["solved", "solved", "solved", "solved", "open", "pending"])
            sla = {"rachat": 30, "transfert": 70, "kyc_documents": 20}.get(cat, 12)
            tickets.append(dict(
                id=800_000 + k, requester_email=_messy_email(str(c["email"]).strip().lower(), rng),
                channel=rng.choice(["email", "telephone", "chat"], p=[.55, .3, .15]),
                category=cat, status=status, priority=rng.choice(["low", "normal", "normal", "high"]),
                created_at=created.to_pydatetime(),
                solved_at=(created + timedelta(hours=float(rng.gamma(2, sla / 2)))).to_pydatetime() if status == "solved" else None,
                satisfaction_rating=(rng.choice(["good", "good", "good", "bad", None]) if status == "solved" else None),
            ))
        return {"raw_crm.contacts": crm, "raw_zendesk.tickets": pd.DataFrame(tickets)}

    def referentiels(self) -> dict[str, pd.DataFrame]:
        produits = pd.DataFrame([
            dict(code=k, label=v["libelle"], wrapper=v["enveloppe"], partner_code=v["partenaire"],
                 min_initial_eur=v["min_initial"], min_scheduled_eur=v["min_programme"],
                 mandate_fee_bps=v["frais_mandat_bps"], wrapper_fee_bps=v["frais_enveloppe_bps"],
                 euro_fund_allowed=v["fonds_euros"], available_profiles=",".join(map(str, v["profils"])),
                 open_from=v["ouvert_du"], open_until=v["ouvert_au"])
            for k, v in R.PRODUITS.items()])
        alloc = []
        for fe in (True, False):
            for p in range(1, 11):
                for s, w in R.allocation(p, fe).items():
                    alloc.append(dict(profile=p, allocation_set="assurance_vie" if fe else "titres_per", support_code=s, target_weight=w))
        promos = pd.DataFrame([
            dict(code=p["code"], offer_type=p["type"], valid_from=p["du"], valid_until=p["au"],
                 eligible_products=",".join(p["produits"]),
                 tiers_json=json.dumps([{"min_initial_eur": a, ("months" if p["type"] == "remboursement_frais" else "prime_eur"): b}
                                        for a, b in p["paliers"]]),
                 global_cap_eur=p["plafond"])
            for p in R.PROMOS])
        supports = pd.DataFrame([dict(code=k, label=v[0], asset_class=v[1], ongoing_charges_bps=v[2]) for k, v in R.SUPPORTS.items()])
        prix = []
        bd = np.where(self.business)[0]
        for i, s in enumerate(self.support_codes):
            prix.append(pd.DataFrame({"support_code": s, "price_date": self.days[bd].date,
                                      "price": np.round(self.support_price[i, bd], 4)}))
        return {
            "raw_app.products": produits,
            "raw_app.profile_allocations": pd.DataFrame(alloc),
            "raw_app.promo_codes": promos,
            "raw_market.supports": supports,
            "raw_market.prix_supports": pd.concat(prix, ignore_index=True),
        }

    def run(self) -> dict[str, pd.DataFrame]:
        print("  marché…", flush=True)
        self.simuler_marche()
        print("  clients…", flush=True)
        self.simuler_clients()
        print("  contrats…", flush=True)
        self.simuler_contrats()
        print("  vie des contrats (simulation quotidienne)…", flush=True)
        self.simuler_vie_des_contrats()
        print("  fichiers partenaires, offres, CRM, support…", flush=True)
        tables = {}
        tables.update(self.referentiels())
        tables.update(self.fichiers_partenaires())
        tables["raw_app.promo_payments"] = self.paiements_offres()
        tables.update(self.crm_et_support())
        tables["raw_app.clients"] = self.clients.drop(columns=["_age"])
        tables["raw_app.contracts"] = self.contrats.drop(columns=[c for c in self.contrats if c.startswith("_")])
        tables["raw_app.movements"] = self.mouvements
        tables["raw_app.mandate_changes"] = self.changements_profil
        return add_fivetran_columns(tables, self.rng)

def add_fivetran_columns(tables: dict[str, pd.DataFrame], rng: np.random.Generator) -> dict[str, pd.DataFrame]:
    synced_base = datetime(2026, 11, 1, 3, 0, 0)
    soft_delete = {"raw_app.clients", "raw_app.movements", "raw_zendesk.tickets", "raw_crm.contacts"}
    duplicates = {"raw_app.movements", "raw_suravenir.valorisations", "raw_ca_titres.positions"}
    out = {}
    for name, df in tables.items():
        df = df.copy()
        df["_fivetran_synced"] = synced_base + pd.to_timedelta(rng.integers(0, 7200, len(df)), unit="s")
        df["_fivetran_deleted"] = False
        if name in soft_delete and len(df):
            idx = rng.choice(df.index, size=max(1, len(df) // 500), replace=False)
            df.loc[idx, "_fivetran_deleted"] = True
        if name in duplicates and len(df):
            dup = df.sample(n=max(1, len(df) // 400), random_state=7)
            dup["_fivetran_synced"] = dup["_fivetran_synced"] + pd.Timedelta(minutes=10)
            df = pd.concat([df, dup], ignore_index=True)
        out[name] = df
    return out

def write_duckdb(tables: dict[str, pd.DataFrame], db_path: str) -> None:
    import duckdb
    con = duckdb.connect(db_path)
    for name, df in tables.items():
        schema, table = name.split(".")
        con.execute(f"create schema if not exists {schema}")
        con.register("tmp_df", df)
        con.execute(f"create or replace table {schema}.{table} as select * from tmp_df")
        con.unregister("tmp_df")
        print(f"  {name:<34} {len(df):>10,} lignes")
    con.close()

def write_parquet(tables: dict[str, pd.DataFrame], out_dir: str) -> None:
    root = pathlib.Path(out_dir)
    for name, df in tables.items():
        schema, table = name.split(".")
        (root / schema).mkdir(parents=True, exist_ok=True)
        df.to_parquet(root / schema / f"{table}.parquet", index=False)
        print(f"  {name:<34} {len(df):>10,} lignes")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=["duckdb", "parquet"], default="duckdb")
    parser.add_argument("--db", default="warehouse.duckdb")
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--clients", type=int, default=6000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(f"Simulation ({args.clients} inscrits, seed={args.seed})")
    tables = Simulation(args.clients, args.seed).run()
    (write_duckdb(tables, args.db) if args.target == "duckdb" else write_parquet(tables, args.out))

if __name__ == "__main__":
    main()
