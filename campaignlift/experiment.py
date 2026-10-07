"""Contrôles de randomisation (phase 1) et tests de l'effet moyen (phase 2)."""

import numpy as np
import pandas as pd
from scipy import stats

from .data import CONTROLE, TRAITEMENTS, matrice_covariables


def test_sample_ratio(segments, proportions=None):
    """Test du χ² d'ajustement des effectifs de groupes (sample ratio mismatch)."""
    observes = pd.Series(segments).value_counts().sort_index()
    if proportions is None:
        proportions = np.full(len(observes), 1 / len(observes))
    attendus = np.asarray(proportions) * observes.sum()
    chi2, p_value = stats.chisquare(observes, attendus)
    return {"chi2": float(chi2), "p_value": float(p_value), "effectifs": observes.to_dict()}


def smd(x_traite, x_controle):
    """Différence standardisée de moyennes, avec variance poolée."""
    return (x_traite.mean() - x_controle.mean()) / np.sqrt((x_traite.var() + x_controle.var()) / 2)


def equilibre_covariables(df):
    """SMD de chaque covariable (catégorielles en indicatrices) pour chaque traitement vs contrôle."""
    X = matrice_covariables(df)
    controle = X[df["segment"] == CONTROLE]
    return pd.DataFrame({g: smd(X[df["segment"] == g], controle) for g in TRAITEMENTS})


def z_test_proportions(x_traite, x_controle):
    """z-test de deux proportions (proportion commune sous H0) et IC95 de la différence (variances séparées)."""
    x_traite, x_controle = np.asarray(x_traite, dtype=float), np.asarray(x_controle, dtype=float)
    n_t, n_c = len(x_traite), len(x_controle)
    p_t, p_c = x_traite.mean(), x_controle.mean()
    p_commun = (x_traite.sum() + x_controle.sum()) / (n_t + n_c)
    z = (p_t - p_c) / np.sqrt(p_commun * (1 - p_commun) * (1 / n_t + 1 / n_c))
    se = np.sqrt(p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c)
    diff = p_t - p_c
    return {"controle": p_c, "traite": p_t, "difference": diff, "ic95": (diff - 1.96 * se, diff + 1.96 * se),
            "lift_relatif": diff / p_c, "z": z, "p_value": 2 * stats.norm.sf(abs(z))}


def test_welch(x_traite, x_controle):
    """Test t de Welch sur une différence de moyennes, avec IC95."""
    res = stats.ttest_ind(x_traite, x_controle, equal_var=False)
    ic = res.confidence_interval(0.95)
    diff = np.mean(x_traite) - np.mean(x_controle)
    return {"controle": np.mean(x_controle), "traite": np.mean(x_traite), "difference": diff,
            "ic95": (ic.low, ic.high), "lift_relatif": diff / np.mean(x_controle),
            "t": res.statistic, "p_value": res.pvalue}


def bootstrap_difference(x_traite, x_controle, n_boot=5000, graine=42):
    """Distribution bootstrap de la différence de moyennes (rééchantillonnage indépendant des deux groupes)."""
    rng = np.random.default_rng(graine)
    x_t, x_c = np.asarray(x_traite), np.asarray(x_controle)
    return np.array([rng.choice(x_t, len(x_t)).mean() - rng.choice(x_c, len(x_c)).mean() for _ in range(n_boot)])


def effets_moyens(df):
    """Tableau des ATE de chaque e-mail vs contrôle sur visite, conversion (z-test) et dépense (Welch)."""
    controle = df[df["segment"] == CONTROLE]
    lignes = []
    for g in TRAITEMENTS:
        traite = df[df["segment"] == g]
        for m in ["visit", "conversion", "spend"]:
            test = test_welch if m == "spend" else z_test_proportions
            r = test(traite[m], controle[m])
            lignes.append({"traitement": g, "metrique": m, "controle": r["controle"], "traite": r["traite"],
                           "difference": r["difference"], "ic95_bas": r["ic95"][0], "ic95_haut": r["ic95"][1],
                           "lift_relatif": r["lift_relatif"], "p_value": r["p_value"]})
    return pd.DataFrame(lignes)
