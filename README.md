# CampaignLift — Mesurer et cibler l'effet causal d'une campagne e-mail

[![tests](https://github.com/mimouniahmed/CampaignLift/actions/workflows/tests.yml/badge.svg)](https://github.com/mimouniahmed/CampaignLift/actions/workflows/tests.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**Français** · [English](README.en.md)

Analyse de bout en bout d'une **expérience marketing randomisée sur 64 000 clients**. Le parcours va de la validation du protocole jusqu'à une **recommandation de ciblage chiffrée en ROI**, en passant par les tests A/B, l'analyse de puissance et les modèles d'uplift.

**Question métier** : la campagne e-mail est-elle rentable, pour quels clients, et quel e-mail envoyer à chacun ?

## Résultats clés

| | |
|---|---|
| **Décision** | Envoyer l'e-mail « Hommes » à **tous** les clients |
| **Effet causal** | **+0,77 $** de chiffre d'affaires par client (IC 95 % : [0,49 ; 1,05]), conversion multipliée par 2,2 |
| **Rentabilité** | **+18 100 $ de profit pour 100 000 clients**, pour 5 000 $ d'envoi (**ROI ≈ 3,6**) |
| **Domaine de validité** | Tant que le coût complet d'un e-mail reste < 0,77 $ × marge (≈ 0,23 $ à 30 % de marge) |
| **Ciblage par uplift** | Pas de gain démontrable : effet homogène pour l'e-mail Hommes ; effet hétérogène et bien modélisé pour l'e-mail Femmes (Qini 0,30, p = 0,002), mais le gain de personnalisation (≈ +2 300 $) est trop faible pour être prouvé |

Hypothèses de la recommandation : 30 % de marge et 0,05 $ par e-mail. Ces hypothèses sont testées sur une grille de sensibilité.

![Profit des politiques de ciblage](docs/figures/05_profit_politiques.png)

➡️ **[Rapport de synthèse](docs/rapport.md)** (décision, chiffres, limites) · **[Méthodologie détaillée](docs/methodologie.md)** (choix techniques et résultats étape par étape)

## Points techniques marquants

- **Validation du protocole avant toute estimation**
  - test de *sample ratio mismatch* ;
  - tests du χ² d'indépendance et différences standardisées (*love plot*).
- **Inférence robuste sur une métrique zéro-inflatée** (99,1 % de clients sans achat)
  - test de Welch validé par bootstrap ;
  - correction de Holm sur 9 comparaisons ;
  - évaluation de l'ajustement ANCOVA / CUPED : gain de précision négligeable ici, et l'analyse explique pourquoi.
- **Analyse de puissance corrigée**
  - une simulation Monte-Carlo montre que la formule standard surestime la puissance pour les événements rares (74 % réels au lieu de 80 % annoncés) ;
  - une formule corrigée est dérivée puis validée par simulation (80,6 %).
- **Modèles d'uplift évalués sans complaisance**
  - méthodes : S-, T- et X-learners, transformation de cible (XGBoost) ;
  - prédictions hors échantillon par cross-fitting, courbes de Qini, test par permutation contre le hasard, calibration par déciles, stabilité sur plusieurs graines ;
  - **détection d'une hétérogénéité artificielle** : pour l'e-mail Hommes, le modèle prédit des écarts entre clients que les données démentent.
- **Interprétabilité** : un arbre substitut résume les segments réceptifs, et l'uplift observé brut les confirme segment par segment.
- **Décision**
  - évaluation hors politique (estimateur IPW de Hájek) sur les données randomisées ;
  - comparaison de politiques par bootstrap apparié, analyse de sensibilité marge × coût ;
  - calcul du coût de la preuve pour la personnalisation.
- **Industrialisation** : package Python, commande en ligne, 17 tests (unitaires et reproduction des résultats des notebooks), intégration continue GitHub Actions.

## Données

**Kevin Hillstrom — MineThatData E-Mail Analytics Challenge (2008)**, jeu de données public ([CSV](http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv)).

64 000 clients ayant acheté dans l'année ont été répartis au hasard en trois groupes égaux pendant deux semaines :
- e-mail **Hommes** ;
- e-mail **Femmes** ;
- **aucun e-mail** (contrôle).

| Type | Colonnes |
|---|---|
| Covariables | `recency`, `history`, `mens`, `womens`, `zip_code`, `newbie`, `channel` |
| Traitement | `segment` |
| Résultats | `visit`, `conversion`, `spend` |

## Démarche

| Notebook | Contenu | Résultat principal |
|---|---|---|
| [01 — Exploration](notebooks/01_exploration.ipynb) | Qualité des données, SRM, équilibre des covariables | Randomisation validée (p = 0,90 ; \|SMD\| ≤ 0,014) |
| [02 — Tests A/B](notebooks/02_ab_tests.ipynb) | z-test, Welch + bootstrap, Holm, ANCOVA, hétérogénéité | Effets significatifs ; l'e-mail Hommes domine ; l'effet passe par le nombre d'acheteurs |
| [03 — Puissance](notebooks/03_power_analysis.ipynb) | MDE, formule corrigée, simulation, sous-groupes | MDE : visite +8 %, conversion +39 %, dépense +50 % |
| [04 — Uplift](notebooks/04_uplift_models.ipynb) | Méta-apprenants, Qini, permutation, déciles, arbre substitut | E-mail Femmes ciblable ; e-mail Hommes homogène |
| [05 — Ciblage et ROI](notebooks/05_targeting_roi.ipynb) | Évaluation hors politique, bootstrap apparié, sensibilité | E-mail Hommes à tous : +18 100 $ / 100 000 clients |

<p align="center">
  <img src="docs/figures/04_courbes_qini.png" width="100%" alt="Courbes de Qini">
</p>

## Installation et reproduction

```bash
git clone https://github.com/mimouniahmed/CampaignLift.git
cd CampaignLift
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

# Données (téléchargées automatiquement par la commande ci-dessous si absentes)
mkdir -p data && curl -L -o data/hillstrom.csv "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"

pytest                                    # 17 tests
campaignlift --marge 0.30 --cout 0.05     # rejoue l'analyse complète et affiche la recommandation
```

Les notebooks s'exécutent dans l'ordre 01 → 05. Le notebook 04 produit `data/uplift_predictions.csv`, que lit le notebook 05.

## Structure

```
CampaignLift/
├── campaignlift/            # package Python
│   ├── data.py              # chargement, covariables, codage du traitement
│   ├── experiment.py        # SRM, SMD, z-test, Welch, bootstrap
│   ├── power.py             # puissance, MDE, taille d'échantillon (formules corrigées)
│   ├── uplift.py            # T-learner en cross-fitting, Qini, test par permutation
│   ├── policy.py            # évaluation hors politique, profit, bootstrap apparié
│   └── cli.py               # commande `campaignlift`
├── notebooks/               # analyse détaillée, 01 → 05
├── tests/                   # tests unitaires + reproduction des résultats
├── docs/
│   ├── rapport.md           # synthèse orientée décision
│   ├── report.md            # synthèse (anglais)
│   ├── methodologie.md      # choix techniques et résultats détaillés
│   └── figures/
└── .github/workflows/       # intégration continue
```

## Stack

Python 3.12 · pandas · NumPy · SciPy · statsmodels · scikit-learn · XGBoost · Matplotlib · pytest · GitHub Actions

## Auteur

**Ahmed Mimouni** — [github.com/mimouniahmed](https://github.com/mimouniahmed)

## Licence

Distribué sous licence [MIT](LICENSE). Le jeu de données Hillstrom est public et n'est pas redistribué dans ce dépôt.
