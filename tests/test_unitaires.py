"""Tests unitaires sur données synthétiques (aucune dépendance au jeu de données réel)."""

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.proportion import proportions_ztest

from campaignlift import experiment, policy, power, uplift


@pytest.fixture
def rng():
    return np.random.default_rng(0)


def test_z_test_identique_a_statsmodels(rng):
    t, c = rng.binomial(1, 0.012, 20_000), rng.binomial(1, 0.006, 20_000)
    r = experiment.z_test_proportions(t, c)
    z, p = proportions_ztest([t.sum(), c.sum()], [len(t), len(c)])
    assert r["z"] == pytest.approx(z)
    assert r["p_value"] == pytest.approx(p)


def test_sample_ratio_equilibre():
    segments = ["a"] * 1000 + ["b"] * 1000 + ["c"] * 1000
    assert experiment.test_sample_ratio(segments)["p_value"] == pytest.approx(1.0)


def test_smd_nulle_pour_echantillons_identiques(rng):
    x = pd.Series(rng.normal(size=500))
    assert experiment.smd(x, x) == pytest.approx(0.0)


def test_bootstrap_proche_de_welch(rng):
    t, c = rng.exponential(2.0, 5000), rng.exponential(1.8, 5000)
    diffs = experiment.bootstrap_difference(t, c, n_boot=2000)
    welch = experiment.test_welch(t, c)
    se_welch = (welch["ic95"][1] - welch["ic95"][0]) / (2 * 1.96)
    assert diffs.std() == pytest.approx(se_welch, rel=0.1)


def test_mde_correspond_a_80_pourcent_de_puissance():
    controle = np.r_[np.ones(60), np.zeros(9940)]          # taux 0,6 %
    d = power.mde(controle, 20_000)
    assert power.puissance_proportion(0.006, d, 20_000) == pytest.approx(0.80, abs=1e-6)
    assert power.n_necessaire(controle, d) == pytest.approx(20_000, rel=1e-4)


def test_formule_corrigee_plus_prudente_que_manuel():
    p = 0.006
    manuel = power.mde_manuel(np.sqrt(p * (1 - p)), 20_000)
    assert power.puissance_proportion(p, manuel, 20_000) < 0.78


def test_puissance_corrigee_validee_par_simulation(rng):
    p, n, delta = 0.006, 20_000, 0.002
    x_c, x_t = rng.binomial(n, p, 20_000), rng.binomial(n, p + delta, 20_000)
    p_commun = (x_c + x_t) / (2 * n)
    z = (x_t - x_c) / n / np.sqrt(p_commun * (1 - p_commun) * 2 / n)
    assert (np.abs(z) > 1.96).mean() == pytest.approx(power.puissance_proportion(p, delta, n), abs=0.015)


def test_qini_oracle_positif_et_hasard_proche_de_zero(rng):
    n = 40_000
    sensible = rng.random(n) < 0.3                       # seuls 30 % des clients réagissent
    t = rng.integers(0, 2, n).astype(float)
    y = rng.binomial(1, 0.02 + 0.05 * sensible * t).astype(float)
    assert uplift.qini_normalise(sensible.astype(float), y, t) > 0.2
    assert abs(uplift.qini_normalise(rng.random(n), y, t)) < 0.1


def test_courbe_qini_finit_sur_l_effet_total(rng):
    t = rng.integers(0, 2, 1000).astype(float)
    y = rng.binomial(1, 0.3, 1000).astype(float)
    q = uplift.courbe_qini(rng.random(1000), y, t)
    attendu = y[t == 1].sum() - y[t == 0].sum() * (t == 1).sum() / (t == 0).sum()
    assert q[-1] == pytest.approx(attendu)


def test_valeur_politique_uniforme_egale_moyenne_du_groupe(rng):
    W = rng.integers(0, 3, 3000)
    y = rng.exponential(1.0, 3000) + W
    for a in range(3):
        assert policy.valeur_politique(np.full(3000, a), W, y) == pytest.approx(y[W == a].mean())


def test_valeur_politique_sans_biais_sur_politique_mixte(rng):
    # Résultats potentiels connus : la politique « oracle » doit être estimée sans biais
    n = 60_000
    x = rng.random(n)
    y0, y1 = rng.binomial(1, 0.1, n), rng.binomial(1, 0.1 + 0.2 * (x > 0.5), n)
    W = rng.integers(0, 2, n)
    y = np.where(W == 1, y1, y0)
    pi = (x > 0.5).astype(int)
    vraie_valeur = np.where(pi == 1, y1, y0).mean()
    assert policy.valeur_politique(pi, W, y) == pytest.approx(vraie_valeur, abs=0.006)


def test_meilleure_action():
    actions = policy.meilleure_action([0.2, -0.1, 0.1, -0.2], [0.1, 0.3, 0.1, -0.1])
    assert list(actions) == [1, 2, 1, 0]
