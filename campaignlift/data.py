"""Chargement du jeu de données Hillstrom et préparation des covariables."""

from pathlib import Path
from urllib.request import urlretrieve

import pandas as pd

URL = "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
CHEMIN_PAR_DEFAUT = Path(__file__).resolve().parent.parent / "data" / "hillstrom.csv"

CONTROLE = "No E-Mail"
TRAITEMENTS = ["Mens E-Mail", "Womens E-Mail"]
CODES_TRAITEMENT = {CONTROLE: 0, "Mens E-Mail": 1, "Womens E-Mail": 2}
METRIQUES = ["visit", "conversion", "spend"]
COVARIABLES = ["recency", "history", "mens", "womens", "newbie", "zip_code", "channel"]


def charger(chemin=CHEMIN_PAR_DEFAUT, telecharger=True):
    """Lit le CSV ; le télécharge d'abord s'il est absent et que `telecharger` est vrai."""
    chemin = Path(chemin)
    if not chemin.exists():
        if not telecharger:
            raise FileNotFoundError(f"{chemin} introuvable (passer telecharger=True pour le récupérer)")
        chemin.parent.mkdir(parents=True, exist_ok=True)
        urlretrieve(URL, chemin)
    return pd.read_csv(chemin)


def matrice_covariables(df):
    """Covariables pré-traitement, catégorielles en indicatrices 0/1 (history_segment est redondant avec history)."""
    return pd.get_dummies(df[COVARIABLES], columns=["zip_code", "channel"], dtype=float)


def codes_traitement(df):
    """0 = aucun e-mail, 1 = e-mail Hommes, 2 = e-mail Femmes."""
    return df["segment"].map(CODES_TRAITEMENT).to_numpy()


def resultats(df):
    """Dictionnaire {métrique : vecteur numpy float}."""
    return {m: df[m].to_numpy(dtype=float) for m in METRIQUES}


def panier_moyen(df):
    """Dépense moyenne des acheteurs (le panier ne dépend pas du traitement, cf. phase 2)."""
    return float(df.loc[df["conversion"] == 1, "spend"].mean())


def groupes(df):
    return {g: df[df["segment"] == g] for g in [CONTROLE] + TRAITEMENTS}
