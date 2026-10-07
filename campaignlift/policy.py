"""Politiques de ciblage, évaluation hors politique et profit (phase 5).

Actions : 0 = aucun e-mail, 1 = e-mail Hommes, 2 = e-mail Femmes.
"""

import numpy as np
import pandas as pd


def valeur_politique(pi, W, y, indices=None):
    """E[y] si chaque client recevait l'action pi(x) : estimateur stratifié par action (IPW de Hájek).

    Valide car l'assignation W est aléatoire et indépendante de pi (prédictions hors échantillon).
    """
    pi, W, y = np.asarray(pi), np.asarray(W), np.asarray(y, dtype=float)
    if indices is not None:
        pi, W, y = pi[indices], W[indices], y[indices]
    valeur = 0.0
    for a in range(3):
        cible = pi == a
        if cible.any():
            observes = cible & (W == a)
            # Garde-fou pour les cibles minuscules sans client ayant reçu a par hasard
            moyenne = y[observes].mean() if observes.any() else y[W == a].mean()
            valeur += cible.mean() * moyenne
    return float(valeur)


def profit(pi, W, spend, marge, cout, indices=None):
    """Profit moyen par client : marge × chiffre d'affaires − coût × part contactée."""
    pi = np.asarray(pi)
    part_contactee = (pi != 0).mean() if indices is None else (pi[indices] != 0).mean()
    return marge * valeur_politique(pi, W, spend, indices) - cout * part_contactee


def meilleure_action(gain_hommes, gain_femmes):
    """Action au plus grand gain net positif, sinon aucun e-mail."""
    gain_hommes, gain_femmes = np.asarray(gain_hommes, dtype=float), np.asarray(gain_femmes, dtype=float)
    return np.select([(gain_hommes >= gain_femmes) & (gain_hommes > 0), (gain_femmes > gain_hommes) & (gain_femmes > 0)],
                     [1, 2], default=0)


def politiques(uplift_hommes, uplift_femmes, ate_hommes, marge, cout):
    """Politiques candidates, à partir des uplifts prédits en $ de chiffre d'affaires."""
    n = len(uplift_femmes)
    gain_femmes = marge * np.asarray(uplift_femmes) - cout
    return {
        "personne": np.zeros(n, dtype=int),
        "tous : e-mail Hommes": np.ones(n, dtype=int),
        "tous : e-mail Femmes": np.full(n, 2),
        "uplift naïf (2 modèles)": meilleure_action(marge * np.asarray(uplift_hommes) - cout, gain_femmes),
        "hybride (Hommes moyen + modèle Femmes)": meilleure_action(np.full(n, marge * ate_hommes - cout), gain_femmes),
    }


def comparer(pols, W, spend, marge, cout, n_boot=1000, graine=42, reference="personne",
             comparaison="tous : e-mail Hommes"):
    """Profit de chaque politique, avec IC95 par bootstrap apparié vs la référence et vs la comparaison."""
    rng = np.random.default_rng(graine)
    n = len(W)
    echantillons = [rng.integers(0, n, n) for _ in range(n_boot)]
    boot = {nom: np.array([profit(pi, W, spend, marge, cout, idx) for idx in echantillons]) for nom, pi in pols.items()}
    point = {nom: profit(pi, W, spend, marge, cout) for nom, pi in pols.items()}
    lignes = []
    for nom in pols:
        vs_ref, vs_cmp = boot[nom] - boot[reference], boot[nom] - boot[comparaison]
        lignes.append({"politique": nom, "profit_par_client": point[nom],
                       "vs_personne": point[nom] - point[reference],
                       "vs_personne_bas": np.percentile(vs_ref, 2.5), "vs_personne_haut": np.percentile(vs_ref, 97.5),
                       "vs_tous_hommes": point[nom] - point[comparaison],
                       "vs_tous_hommes_bas": np.percentile(vs_cmp, 2.5), "vs_tous_hommes_haut": np.percentile(vs_cmp, 97.5),
                       "part_hommes": float((pols[nom] == 1).mean()), "part_femmes": float((pols[nom] == 2).mean())})
    return pd.DataFrame(lignes).set_index("politique")
