# CampaignLift — analyse d'une expérience marketing randomisée

Projet éducatif : analyser, étape par étape, une **expérience marketing randomisée** portant sur 64 000 clients — tests statistiques, analyse de puissance, puis modèles d'**uplift** pour cibler les clients réellement sensibles à la campagne — et aboutir à une **recommandation chiffrée en ROI**. L'objectif premier est d'apprendre (inférence causale, A/B testing, uplift modeling), pas de livrer un rapport rapidement.

## Ce que le projet produira (et ne produira pas)

- **Question métier** : *l'e-mailing vaut-il le coup, pour qui, et combien rapporte-t-il ?*
- **Sortie finale** : une recommandation de ciblage (qui recevoir l'e-mail, lequel) avec son gain attendu en dollars par rapport à « tout le monde » et « personne ».
- **Ce que ce n'est pas** : on ne prédit pas *qui achète* (modèle de réponse classique), mais *qui achète **à cause** de l'e-mail* (effet causal individuel). Toute la différence du projet est là.

## Méthode de travail

- Tout est développé en **notebooks Jupyter**, un concept par cellule, exécuté et observé avant de passer au suivant.
- Chaque bout de code est expliqué dans la conversation avant/au moment de l'écrire (pas seulement en commentaire) — l'utilisateur veut comprendre chaque brique, pas se faire livrer du code.
- Le projet avance par phases, chacune validée avant de passer à la suivante.
- **Ce README est tenu exhaustif en permanence** : c'est le seul artefact qui voyage avec le dépôt Git et qui reste lisible sans l'historique de conversation (utile pour reprendre le projet sur une autre machine).
- Même approche que le projet LOL-assistant : notebooks d'abord, industrialisation en package Python une fois les briques stabilisées.

## Le jeu de données

**Kevin Hillstrom — MineThatData E-Mail Analytics Challenge (2008)**, public : [CSV source](http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv), stocké localement dans `data/hillstrom.csv` (non versionné).

64 000 clients ayant acheté dans les 12 derniers mois, **répartis aléatoirement** en trois groupes pendant deux semaines :
- 1/3 reçoit un e-mail de campagne **Hommes** (`Mens E-Mail`),
- 1/3 reçoit un e-mail de campagne **Femmes** (`Womens E-Mail`),
- 1/3 ne reçoit **rien** (`No E-Mail`, groupe contrôle).

| Colonne | Signification |
|---|---|
| `recency` | mois depuis le dernier achat |
| `history_segment` / `history` | montant dépensé sur l'année passée (tranche / valeur en $) |
| `mens` / `womens` | a acheté des produits hommes / femmes l'année passée (0/1) |
| `zip_code` | Urban / Suburban / Rural (orthographié `Surburban` dans le fichier) |
| `newbie` | nouveau client sur les 12 derniers mois (0/1) |
| `channel` | canal d'achat l'année passée : Phone / Web / Multichannel |
| `segment` | **traitement** assigné aléatoirement |
| `visit` / `conversion` / `spend` | **résultats** sur les deux semaines suivantes : visite du site, achat, montant dépensé |

## Architecture globale de l'analyse

```
CSV brut → exploration + vérification de la randomisation → tests A/B (effet moyen)
        → analyse de puissance → modèles d'uplift (effet individuel) → politique de ciblage + ROI
```

## Statut global (2026-10-01)

| Phase | Statut |
|---|---|
| 0. Mise en place (venv, données, README) | ✅ Terminée |
| 1. Exploration + vérification de la randomisation | ✅ Terminée — randomisation validée |
| 2. Tests statistiques (effet moyen du traitement) | 🚧 En cours |
| 3. Analyse de puissance | ⏳ À faire |
| 4. Modèles d'uplift | ⏳ À faire |
| 5. Politique de ciblage + ROI | ⏳ À faire |
| 6. Industrialisation (package `campaignlift/`) + rapport final | ⏳ À faire |

## Phase 0 — Mise en place ✅ Terminée

- `.venv` à la racine (Python 3.12.10, `C:\Users\lexoo\AppData\Local\Programs\Python\Python312`), dépendances de `requirements.txt` installées.
- Noyau Jupyter enregistré sous le nom **`campaignlift`** (« Python (campaignlift) ») — à sélectionner dans VSCode pour les notebooks.
- Données téléchargées dans `data/hillstrom.csv` (64 000 lignes + en-tête).

## Phase 1 — Exploration + vérification de la randomisation ✅ Terminée

Fichier : [`notebooks/01_exploration.ipynb`](notebooks/01_exploration.ipynb)

Objectifs :
1. Charger et comprendre la structure des données (types, valeurs manquantes, distributions).
   - ✅ Fait — 64 000 lignes × 12 colonnes, aucune valeur manquante ; avec pandas 3, les colonnes texte ont le type `str` (et non plus `object`).
2. Vérifier que les trois groupes ont bien des tailles équilibrées (*sample ratio mismatch*).
   - ✅ Fait — test du χ² d'ajustement (`scipy.stats.chisquare`) contre une répartition 1/3 – 1/3 – 1/3 : effectifs 21 387 / 21 307 / 21 306, χ² = 0,203 (2 ddl), **p = 0,904** → aucun *sample ratio mismatch*. Seuil retenu pour ce contrôle : 0,001, une convention courante pour un test de *sample ratio mismatch* qui évite les fausses alertes.
3. Vérifier l'**équilibre des covariables** entre groupes (tests du χ², différences standardisées) : c'est ce qui justifie d'interpréter les différences de résultats comme **causales**.
   - ✅ Tests du χ² d'indépendance (`scipy.stats.chi2_contingency`) groupe × covariable, sur `recency` (traitée comme catégorielle, 12 valeurs), `history_segment`, `mens`, `womens`, `zip_code`, `newbie`, `channel` : toutes les p-values sont ≥ 0,358 (minimum atteint sur `history_segment`) → aucun déséquilibre détecté. Point de vigilance noté : 7 tests simultanés, donc environ 0,35 faux positif attendu à 5 % (comparaisons multiples).
   - ✅ Différences standardisées (SMD, variance poolée, catégorielles en indicatrices 0/1), chaque groupe traité vs `No E-Mail`, sur 11 colonnes dont `history` en continu : |SMD| max = **0,014** (`zip_code_Rural`, e-mail Hommes), soit 7× sous le seuil usuel de 0,1 (Austin, 2009). Visualisé par un *love plot* (`docs/figures/01_love_plot.png`).
   - Pourquoi les deux outils : la p-value mélange ampleur et taille d'échantillon (avec n = 64 000, tout écart finit par être « significatif ») ; la SMD ne mesure que l'ampleur.
4. Premier coup d'œil aux taux de visite / conversion / dépense par groupe.
   - ✅ Fait (`docs/figures/01_resultats_par_groupe.png`) :

     | Groupe | Visite | Conversion | Dépense moyenne |
     |---|---|---|---|
     | No E-Mail | 10,62 % | 0,573 % | 0,653 $ |
     | Mens E-Mail | 18,28 % | 1,253 % | 1,423 $ |
     | Womens E-Mail | 15,14 % | 0,884 % | 1,077 $ |

   - **Forme de `spend`** : 99,10 % de zéros (578 acheteurs sur 64 000), montants de 30 $ à 499 $ chez les acheteurs (moyenne ≈ 114–122 $ selon le groupe). Variable **zéro-inflatée** et très asymétrique → conditionne le choix des tests en phase 2.

**Conclusion** : la randomisation a fonctionné (pas de *sample ratio mismatch*, covariables équilibrées), donc les écarts de résultats entre groupes s'interprètent comme des **effets causaux** des e-mails. Elle équilibre aussi en espérance les variables *non observées*, ce qu'aucune méthode observationnelle ne garantit.

## Phase 2 — Tests statistiques ⏳ À faire

Prévu : test de différence de proportions (z-test) sur visite/conversion, Welch t-test et bootstrap sur la dépense (distribution très asymétrique, majoritairement des zéros), intervalles de confiance, correction pour comparaisons multiples (3 groupes × 3 métriques), régression avec covariables (CUPED / ANCOVA) pour réduire la variance.

## Phase 3 — Analyse de puissance ⏳ À faire

Prévu : effet minimal détectable (MDE) avec cette taille d'échantillon, taille d'échantillon nécessaire pour détecter un effet donné, explication de pourquoi la conversion (événement rare) est bien plus difficile à tester que la visite.

## Phase 4 — Modèles d'uplift ⏳ À faire

Prévu : S-learner, T-learner, transformation de la cible (*class transformation*), éventuellement X-learner ; évaluation par courbes d'uplift / Qini et AUUC sur un jeu de test. Comparaison avec un modèle de réponse classique pour montrer la différence.

## Phase 5 — Politique de ciblage + ROI ⏳ À faire

Prévu : hypothèses de coût par e-mail et de marge, comparaison de politiques (personne / tout le monde / meilleur e-mail par client selon l'uplift / top-k %), gain attendu en $ avec intervalle de confiance.

## Phase 6 — Industrialisation + rapport ⏳ À faire

Prévu : extraire les briques stabilisées dans un package `campaignlift/` (comme `lol_assistant/`), et rédiger la recommandation finale.

## Dépôt Git / GitHub

- Dépôt : [github.com/mimouniahmed/CampaignLift](https://github.com/mimouniahmed/CampaignLift), remote `origin` en SSH (`git@github.com:mimouniahmed/CampaignLift.git`), branche `main`.
- Sur cette machine Windows, l'accès SSH passe par la clé `~/.ssh/gitcreteil` (déclarée dans `~/.ssh/config`), la même que pour LOL-assistant.

## Reprendre le projet sur une nouvelle machine

Ce qui **suit le dépôt Git** : le code, les notebooks, ce README, `.gitignore`, `requirements.txt`.

Ce qui **ne suit pas le dépôt** (exclu par `.gitignore`) :
1. **`data/hillstrom.csv`** — se re-télécharge en une commande (voir ci-dessous), aucune donnée privée.
2. **`.venv/`** — à recréer.
3. **La clé SSH pour push/pull sur GitHub** — générer une clé (`ssh-keygen`) et l'ajouter sur [github.com/settings/ssh/new](https://github.com/settings/ssh/new).
4. **L'historique de conversation et la mémoire Claude Code** — locaux à la machine ; ce README sert de filet de sécurité.

```bash
git clone git@github.com:mimouniahmed/CampaignLift.git
cd CampaignLift
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Linux/macOS : .venv/bin/python
.venv/Scripts/python -m ipykernel install --user --name campaignlift --display-name "Python (campaignlift)"
mkdir data
curl -L -o data/hillstrom.csv "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
```

## Structure du projet

```
CampaignLift/
├── README.md
├── requirements.txt
├── .gitignore
├── data/                      # non versionné
│   └── hillstrom.csv
└── notebooks/
    └── 01_exploration.ipynb
```
