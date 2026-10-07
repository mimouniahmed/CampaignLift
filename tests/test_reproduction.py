"""Le package reproduit les chiffres clés des notebooks (sauté si data/hillstrom.csv est absent)."""

import numpy as np
import pytest

from campaignlift import experiment, policy, power, uplift
from campaignlift.data import (CHEMIN_PAR_DEFAUT, CONTROLE, charger, codes_traitement, matrice_covariables,
                               panier_moyen, resultats)

pytestmark = pytest.mark.skipif(not CHEMIN_PAR_DEFAUT.exists(), reason="data/hillstrom.csv absent")


@pytest.fixture(scope="module")
def df():
    return charger(telecharger=False)


@pytest.fixture(scope="module")
def predictions(df):
    X, W, Y = matrice_covariables(df), codes_traitement(df), resultats(df)
    return uplift.t_learner(X, W, Y["conversion"])


def test_phase1_randomisation(df):
    assert experiment.test_sample_ratio(df["segment"])["p_value"] == pytest.approx(0.904, abs=1e-3)
    assert experiment.equilibre_covariables(df).abs().max().max() == pytest.approx(0.0137, abs=1e-4)


def test_phase2_effets_moyens(df):
    effets = experiment.effets_moyens(df).set_index(["traitement", "metrique"])
    assert effets.loc[("Mens E-Mail", "spend"), "difference"] == pytest.approx(0.770, abs=1e-3)
    assert effets.loc[("Womens E-Mail", "spend"), "difference"] == pytest.approx(0.424, abs=1e-3)
    assert effets.loc[("Mens E-Mail", "conversion"), "difference"] == pytest.approx(0.00681, abs=1e-5)
    assert effets["p_value"].max() < 0.01


def test_phase3_mde(df):
    controle = df[df["segment"] == CONTROLE]
    n = len(controle)
    assert power.mde(controle["conversion"], n) / controle["conversion"].mean() == pytest.approx(0.391, abs=0.005)
    assert power.mde(controle["spend"], n, binaire=False) == pytest.approx(0.326, abs=0.005)


def test_phase4_qini(df, predictions):
    W, y = codes_traitement(df), resultats(df)["conversion"]
    assert uplift.evaluer(predictions[:, 2] - predictions[:, 0], y, W, 2) == pytest.approx(0.295, abs=0.005)
    assert abs(uplift.evaluer(predictions[:, 1] - predictions[:, 0], y, W, 1)) < 0.05


def test_phase5_politiques(df, predictions):
    W, spend = codes_traitement(df), resultats(df)["spend"]
    panier = panier_moyen(df)
    ate_hommes = spend[W == 1].mean() - spend[W == 0].mean()
    pols = policy.politiques((predictions[:, 1] - predictions[:, 0]) * panier,
                             (predictions[:, 2] - predictions[:, 0]) * panier, ate_hommes, 0.30, 0.05)
    tous_hommes = policy.profit(pols["tous : e-mail Hommes"], W, spend, 0.30, 0.05)
    personne = policy.profit(pols["personne"], W, spend, 0.30, 0.05)
    hybride = policy.profit(pols["hybride (Hommes moyen + modèle Femmes)"], W, spend, 0.30, 0.05)
    assert (tous_hommes - personne) * 100_000 == pytest.approx(18_095, abs=5)
    assert (hybride - tous_hommes) * 100_000 == pytest.approx(2_305, abs=5)
    assert np.mean(pols["hybride (Hommes moyen + modèle Femmes)"] == 2) == pytest.approx(0.21, abs=0.01)
