"""Modèles d'uplift en cross-fitting et évaluation par courbe de Qini (phase 4)."""

import numpy as np
import xgboost as xgb
from sklearn.model_selection import StratifiedKFold

PARAMS_XGB = dict(n_estimators=200, max_depth=3, learning_rate=0.03, min_child_weight=20,
                  subsample=0.8, colsample_bytree=0.8, reg_lambda=5, n_jobs=-1, verbosity=0)


def classifieur(**kw):
    """XGBoost peu profond et régularisé : le signal d'uplift est faible."""
    return xgb.XGBClassifier(**{**PARAMS_XGB, **kw})


def plis(X, W, y, k=5, graine=0):
    """Plis stratifiés sur (traitement × résultat)."""
    strates = np.asarray(W) * 2 + np.asarray(y).astype(int)
    return list(StratifiedKFold(k, shuffle=True, random_state=graine).split(X, strates))


def t_learner(X, W, y, fabrique=classifieur, k=5, graine=0):
    """T-learner en cross-fitting : matrice n × 3 des P(y | x, action a) hors échantillon.

    L'uplift de l'action a est la colonne a moins la colonne 0.
    """
    W, y = np.asarray(W), np.asarray(y, dtype=float)
    P = np.zeros((len(y), 3))
    for train, test in plis(X, W, y, k, graine):
        for a in range(3):
            lignes = train[W[train] == a]
            modele = fabrique().fit(X.iloc[lignes], y[lignes])
            P[test, a] = modele.predict_proba(X.iloc[test])[:, 1]
    return P


def courbe_qini(uplift, y, t):
    """Q(k) = Y_T(k) − Y_C(k)·N_T(k)/N_C(k), clients triés par uplift prédit décroissant."""
    ordre = np.argsort(-np.asarray(uplift), kind="stable")
    y, t = np.asarray(y, dtype=float)[ordre], np.asarray(t, dtype=float)[ordre]
    n_t, n_c = np.cumsum(t), np.cumsum(1 - t)
    y_t, y_c = np.cumsum(y * t), np.cumsum(y * (1 - t))
    return y_t - y_c * np.divide(n_t, n_c, out=np.zeros(len(y)), where=n_c > 0)


def qini_normalise(uplift, y, t):
    """Écart moyen entre la courbe de Qini et la diagonale, en fraction de l'effet total (0 = hasard)."""
    q = courbe_qini(uplift, y, t)
    diagonale = q[-1] * np.arange(1, len(q) + 1) / len(q)
    return float((q - diagonale).mean() / q[-1])


def evaluer(uplift, y, W, traitement):
    """Qini normalisé sur la paire traitement vs contrôle."""
    W = np.asarray(W)
    masque = (W == traitement) | (W == 0)
    return qini_normalise(np.asarray(uplift)[masque], np.asarray(y)[masque], (W[masque] == traitement).astype(float))


def p_value_permutation(score, y, W, traitement, n_permutations=500, graine=0):
    """p-value empirique : part des classements aléatoires dont le Qini atteint `score`."""
    rng = np.random.default_rng(graine)
    nulles = np.array([evaluer(rng.random(len(W)), y, W, traitement) for _ in range(n_permutations)])
    return float((1 + (nulles >= score).sum()) / (1 + n_permutations))
