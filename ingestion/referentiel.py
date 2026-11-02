"""Référentiel métier de la simulation : produits, partenaires, profils, frais et offres.

Les hypothèses de simulation sont détaillées dans le README (section « Les données »).
"""

from __future__ import annotations

from datetime import date

START = date(2022, 1, 1)
END = date(2026, 10, 31)

PRODUITS = {
    "assurance_vie": dict(
        libelle="Assurance-vie en gestion pilotée", enveloppe="assurance_vie", partenaire="SURAVENIR",
        profils=list(range(2, 11)), min_initial=1000, min_programme=50,
        frais_mandat_bps=70, frais_enveloppe_bps=60, fonds_euros=True,
        ouvert_du=date(2015, 1, 1), ouvert_au=None, part=0.52,
    ),
    "assurance_vie_kids": dict(
        libelle="Assurance-vie enfant", enveloppe="assurance_vie", partenaire="SURAVENIR",
        profils=list(range(4, 11)), min_initial=1000, min_programme=50,
        frais_mandat_bps=70, frais_enveloppe_bps=60, fonds_euros=True,
        ouvert_du=date(2019, 1, 1), ouvert_au=None, part=0.0,
    ),
    "per_bancaire": dict(
        libelle="PER bancaire (compte-titres)", enveloppe="per", partenaire="CA_TITRES",
        profils=list(range(2, 11)), min_initial=1000, min_programme=150,
        frais_mandat_bps=70, frais_enveloppe_bps=30, fonds_euros=False,
        ouvert_du=date(2020, 1, 1), ouvert_au=date(2024, 2, 29), part=0.12,
    ),
    "per_assurantiel": dict(
        libelle="PER assurantiel Retraite+", enveloppe="per", partenaire="SPIRICA",
        profils=list(range(2, 11)), min_initial=1000, min_programme=50,
        frais_mandat_bps=70, frais_enveloppe_bps=50, fonds_euros=False,
        ouvert_du=date(2024, 3, 1), ouvert_au=None, part=0.12,
    ),
    "pea": dict(
        libelle="PEA en gestion pilotée", enveloppe="pea", partenaire="CA_TITRES",
        profils=[10], min_initial=1000, min_programme=50,
        frais_mandat_bps=70, frais_enveloppe_bps=60, fonds_euros=False,
        ouvert_du=date(2015, 1, 1), ouvert_au=None, part=0.15,
    ),
    "cto": dict(
        libelle="Compte-titres en gestion pilotée", enveloppe="cto", partenaire="CA_TITRES",
        profils=list(range(2, 11)), min_initial=1000, min_programme=50,
        frais_mandat_bps=70, frais_enveloppe_bps=60, fonds_euros=False,
        ouvert_du=date(2015, 1, 1), ouvert_au=None, part=0.09,
    ),
}

PARTENAIRES = {
    "SURAVENIR": dict(nom="Suravenir", type="assureur"),
    "SPIRICA": dict(nom="Spirica", type="assureur"),
    "CA_TITRES": dict(nom="Crédit Agricole Titres", type="teneur_de_compte"),
}

SUPPORTS = {
    "ETF_ACTIONS_MONDE":     ("ETF Actions Monde", "actions", 20),
    "ETF_ACTIONS_EUROPE":    ("ETF Actions Europe", "actions", 15),
    "ETF_ACTIONS_EMERGENTS": ("ETF Actions Émergents", "actions", 25),
    "ETF_OBLIG_EURO":        ("ETF Obligations Euro", "obligations", 12),
    "ETF_OBLIG_MONDE":       ("ETF Obligations Monde couvertes", "obligations", 15),
    "MONETAIRE_EURO":        ("Fonds monétaire euro", "monetaire", 10),
    "FONDS_EUROS":           ("Fonds en euros (assureur)", "fonds_euros", 0),
}

RENDEMENTS_ANNUELS = {

    "ETF_ACTIONS_MONDE":     [-0.13, 0.18,  0.25,  0.07,  0.08],
    "ETF_ACTIONS_EUROPE":    [-0.10, 0.15,  0.08,  0.12,  0.07],
    "ETF_ACTIONS_EMERGENTS": [-0.15, 0.06,  0.14,  0.15,  0.10],
    "ETF_OBLIG_EURO":        [-0.17, 0.07,  0.02,  0.01,  0.02],
    "ETF_OBLIG_MONDE":       [-0.13, 0.05,  0.02,  0.03,  0.02],
    "MONETAIRE_EURO":        [ 0.00, 0.033, 0.037, 0.022, 0.017],
    "FONDS_EUROS":           [ 0.020, 0.026, 0.030, 0.030, 0.025],
}
VOLATILITES = {
    "ETF_ACTIONS_MONDE": 0.15, "ETF_ACTIONS_EUROPE": 0.17, "ETF_ACTIONS_EMERGENTS": 0.19,
    "ETF_OBLIG_EURO": 0.06, "ETF_OBLIG_MONDE": 0.05, "MONETAIRE_EURO": 0.002, "FONDS_EUROS": 0.0,
}

PART_ACTIONS = {1: 0.00, 2: 0.10, 3: 0.20, 4: 0.30, 5: 0.40, 6: 0.50, 7: 0.62, 8: 0.75, 9: 0.88, 10: 1.00}
PART_FONDS_EUROS_AV = {1: 1.00, 2: 0.75, 3: 0.60, 4: 0.40, 5: 0.20, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0}
REPARTITION_ACTIONS = {"ETF_ACTIONS_MONDE": 0.60, "ETF_ACTIONS_EUROPE": 0.25, "ETF_ACTIONS_EMERGENTS": 0.15}
REPARTITION_OBLIG = {"ETF_OBLIG_EURO": 0.60, "ETF_OBLIG_MONDE": 0.40}

def allocation(profil: int, avec_fonds_euros: bool) -> dict[str, float]:
    """Allocation cible d'un profil. Hors assurance-vie, le fonds en euros est remplacé par un fonds monétaire."""
    actions = PART_ACTIONS[profil]
    securise = PART_FONDS_EUROS_AV[profil]
    oblig = max(0.0, 1 - actions - securise)
    alloc = {s: actions * w for s, w in REPARTITION_ACTIONS.items()}
    alloc.update({s: oblig * w for s, w in REPARTITION_OBLIG.items()})
    alloc["FONDS_EUROS" if avec_fonds_euros else "MONETAIRE_EURO"] = securise
    return {k: round(v, 4) for k, v in alloc.items() if v > 0}

PROMOS = [
    dict(code="BIENVENUE22", type="prime", du=date(2022, 3, 1), au=date(2022, 5, 31),
         produits=["assurance_vie"], paliers=[(10000, 100), (25000, 250), (50000, 500)], plafond=500),
    dict(code="RENTREE22", type="remboursement_frais", du=date(2022, 9, 1), au=date(2022, 10, 31),
         produits=["assurance_vie", "pea", "cto"], paliers=[(5000, 3)], plafond=50),
    dict(code="PRINTEMPS23", type="remboursement_frais", du=date(2023, 3, 15), au=date(2023, 5, 31),
         produits=["assurance_vie", "pea", "cto", "per_bancaire"], paliers=[(10000, 6), (25000, 7), (50000, 8)], plafond=500),
    dict(code="PRIME24", type="prime", du=date(2024, 3, 13), au=date(2024, 6, 30),
         produits=["assurance_vie", "per_assurantiel"], paliers=[(10000, 100), (25000, 250), (50000, 500)], plafond=500),
    dict(code="FRAIS24", type="remboursement_frais", du=date(2024, 9, 1), au=date(2024, 12, 15),
         produits=["assurance_vie", "pea", "cto", "per_assurantiel"], paliers=[(10000, 6), (25000, 7), (50000, 8)], plafond=500),
    dict(code="PRINTEMPS25", type="remboursement_frais", du=date(2025, 4, 1), au=date(2025, 5, 31),
         produits=["assurance_vie", "pea", "cto", "per_assurantiel"], paliers=[(5000, 3)], plafond=50),
    dict(code="RETRAITE25", type="remboursement_frais", du=date(2025, 10, 1), au=date(2025, 12, 23),
         produits=["per_assurantiel"], paliers=[(5000, 6), (15000, 8), (50000, 10)], plafond=500),
    dict(code="PILOTE26", type="prime", du=date(2026, 4, 1), au=date(2026, 6, 30),
         produits=["assurance_vie"], paliers=[(10000, 150), (50000, 500), (100000, 1500)], plafond=1500),
    dict(code="RETRAITE26", type="remboursement_frais", du=date(2026, 10, 1), au=date(2026, 12, 23),
         produits=["per_assurantiel"], paliers=[(5000, 6), (15000, 8), (50000, 10)], plafond=500),
]

CANAUX = {
    "seo": 0.20, "sea": 0.22, "parrainage": 0.16, "comparateur": 0.10,
    "partenariat_media": 0.08, "influence": 0.07, "direct": 0.17,
}
OBJECTIFS = {"preparer_retraite": 0.27, "faire_fructifier": 0.33, "projet_moyen_terme": 0.15,
             "transmettre": 0.08, "epargne_precaution": 0.10, "financer_etudes_enfants": 0.07}
CSP = {"cadre": 0.46, "profession_intermediaire": 0.16, "independant": 0.12, "employe": 0.10,
       "profession_liberale": 0.08, "retraite": 0.06, "etudiant": 0.02}
CATEGORIES_TICKETS = {"versement": 0.17, "rachat": 0.13, "fiscalite": 0.14, "transfert": 0.07,
                      "changement_profil": 0.09, "offre_promotionnelle": 0.08, "connexion": 0.12,
                      "performance": 0.08, "kyc_documents": 0.12}
