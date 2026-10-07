"""Puissance, MDE et taille d'échantillon (phase 3).

Formules corrigées : la formule « de manuel » à variances égales surestime la puissance pour les
événements rares. Pour une proportion, on distingue la variance sous H0 (seuil de rejet, proportion
commune) et la variance sous H1. Pour une dépense zéro-inflatée, on suppose σ_T² ≈ σ_C² × (1 + lift),
puisque l'e-mail multiplie le nombre d'acheteurs sans changer le panier.
"""

import numpy as np
from scipy import optimize, stats


def puissance_proportion(p_controle, delta, n, alpha=0.05):
    """Puissance d'un z-test bilatéral de deux proportions, n clients par groupe."""
    z = stats.norm.ppf(1 - alpha / 2)
    p_traite = p_controle + delta
    p_bar = (p_controle + p_traite) / 2
    se0 = np.sqrt(2 * p_bar * (1 - p_bar) / n)
    se1 = np.sqrt((p_controle * (1 - p_controle) + p_traite * (1 - p_traite)) / n)
    return stats.norm.sf((z * se0 - delta) / se1) + stats.norm.cdf((-z * se0 - delta) / se1)


def puissance_depense(moyenne_controle, sigma_controle, delta, n, alpha=0.05):
    """Puissance pour une dépense zéro-inflatée, avec σ_T² ≈ σ_C² × (1 + lift)."""
    z = stats.norm.ppf(1 - alpha / 2)
    var_c = sigma_controle ** 2
    se0 = np.sqrt(2 * var_c / n)
    se1 = np.sqrt((var_c + var_c * (1 + delta / moyenne_controle)) / n)
    return stats.norm.sf((z * se0 - delta) / se1) + stats.norm.cdf((-z * se0 - delta) / se1)


def _fonction_puissance(y_controle, binaire):
    y_controle = np.asarray(y_controle, dtype=float)
    base = y_controle.mean()
    if binaire:
        return base, lambda delta, n: puissance_proportion(base, delta, n)
    sigma = y_controle.std(ddof=1)
    return base, lambda delta, n: puissance_depense(base, sigma, delta, n)


def mde(y_controle, n, binaire=True, puissance=0.80):
    """Plus petit effet absolu détectable avec la puissance demandée (α = 5 %), n clients par groupe."""
    base, f = _fonction_puissance(y_controle, binaire)
    return optimize.brentq(lambda d: f(d, n) - puissance, 1e-9, 5 * base)


def n_necessaire(y_controle, delta, binaire=True, puissance=0.80):
    """Clients nécessaires par groupe pour détecter un effet absolu delta."""
    _, f = _fonction_puissance(y_controle, binaire)
    return optimize.brentq(lambda n: f(delta, n) - puissance, 2, 1e10)


def mde_manuel(sigma, n, alpha=0.05, puissance=0.80):
    """Formule de manuel (variances égales) : MDE ≈ 2,8 σ √(2/n)."""
    return (stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(puissance)) * sigma * np.sqrt(2 / n)
