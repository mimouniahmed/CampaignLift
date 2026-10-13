# Méthodologie détaillée

Ce document détaille, étape par étape, les choix méthodologiques et les résultats chiffrés de l'analyse. La synthèse orientée décision se trouve dans [`rapport.md`](rapport.md). Chaque section renvoie au notebook correspondant.

## 1. Exploration et validation de la randomisation

Notebook : [`notebooks/01_exploration.ipynb`](../notebooks/01_exploration.ipynb)

Étapes :
1. Charger et comprendre la structure des données (types, valeurs manquantes, distributions).
   - 64 000 lignes × 12 colonnes, aucune valeur manquante ; colonnes texte de type `str` (pandas 3).
2. Vérifier que les trois groupes ont bien des tailles équilibrées (*sample ratio mismatch*).
   - test du χ² d'ajustement (`scipy.stats.chisquare`) contre une répartition 1/3 – 1/3 – 1/3 : effectifs 21 387 / 21 307 / 21 306, χ² = 0,203 (2 ddl), **p = 0,904** → aucun *sample ratio mismatch*. Seuil retenu pour ce contrôle : 0,001, une convention courante pour un test de *sample ratio mismatch* qui évite les fausses alertes.
3. Vérifier l'**équilibre des covariables** entre groupes (tests du χ², différences standardisées) : c'est ce qui justifie d'interpréter les différences de résultats comme **causales**.
   - Tests du χ² d'indépendance (`scipy.stats.chi2_contingency`) groupe × covariable, sur `recency` (traitée comme catégorielle, 12 valeurs), `history_segment`, `mens`, `womens`, `zip_code`, `newbie`, `channel` : toutes les p-values sont ≥ 0,358 (minimum atteint sur `history_segment`) → aucun déséquilibre détecté. Point de vigilance noté : 7 tests simultanés, donc environ 0,35 faux positif attendu à 5 % (comparaisons multiples).
   - Différences standardisées (SMD, variance poolée, catégorielles en indicatrices 0/1), chaque groupe traité vs `No E-Mail`, sur 11 colonnes dont `history` en continu : |SMD| max = **0,014** (`zip_code_Rural`, e-mail Hommes), soit 7× sous le seuil usuel de 0,1 (Austin, 2009). Visualisé par un *love plot* (`figures/01_love_plot.png`).
   - Pourquoi les deux outils : la p-value mélange ampleur et taille d'échantillon (avec n = 64 000, tout écart finit par être « significatif ») ; la SMD ne mesure que l'ampleur.
4. Résultats bruts par groupe.
   - Figure (`figures/01_resultats_par_groupe.png`) :

     | Groupe | Visite | Conversion | Dépense moyenne |
     |---|---|---|---|
     | No E-Mail | 10,62 % | 0,573 % | 0,653 $ |
     | Mens E-Mail | 18,28 % | 1,253 % | 1,423 $ |
     | Womens E-Mail | 15,14 % | 0,884 % | 1,077 $ |

   - **Forme de `spend`** : 99,10 % de zéros (578 acheteurs sur 64 000), montants de 30 $ à 499 $ chez les acheteurs (moyenne ≈ 114–122 $ selon le groupe). Variable **zéro-inflatée** et très asymétrique → conditionne le choix des tests en section 2.

**Conclusion** : la randomisation a fonctionné (pas de *sample ratio mismatch*, covariables équilibrées), donc les écarts de résultats entre groupes s'interprètent comme des **effets causaux** des e-mails. Elle équilibre aussi en espérance les variables *non observées*, ce qu'aucune méthode observationnelle ne garantit.

## 2. Effet moyen des e-mails (tests A/B)

Notebook : [`notebooks/02_ab_tests.ipynb`](../notebooks/02_ab_tests.ipynb)

**Estimand** : l'effet moyen du traitement (ATE), estimé sans biais par une simple différence de moyennes grâce à la randomisation.

**Résultats** (chaque e-mail vs `No E-Mail`) :

| | E-mail Hommes | E-mail Femmes |
|---|---|---|
| Visite | +7,66 pts [6,99 ; 8,32] (10,62 % → 18,28 %, +72 %) | +4,52 pts [3,89 ; 5,16] (→ 15,14 %, +43 %) |
| Conversion | +0,68 pt [0,50 ; 0,86] (0,573 % → 1,253 %, +119 %) | +0,31 pt [0,15 ; 0,47] (→ 0,884 %, +54 %) |
| Dépense / client | +0,77 $ [0,49 ; 1,05] (+118 %) | +0,42 $ [0,17 ; 0,68] (+65 %) |

**Méthodes et décisions** :
- **Proportions** : z-test de deux proportions codé à la main (proportion commune sous H₀ pour le test, variances séparées pour l'IC), vérifié contre `statsmodels.stats.proportion.proportions_ztest` (z identique : 7,3851).
- **Dépense** : test de **Welch** (pas de Student : pas d'hypothèse de variances égales). Validité malgré 99 % de zéros vérifiée par **bootstrap percentile** (5 000 rééchantillonnages, graine 42) : IC quasi identiques (Hommes : Welch [0,485 ; 1,055] vs bootstrap [0,479 ; 1,049]) → le TCL tient à n ≈ 21 000 (`figures/02_bootstrap_spend.png`).
- **Décomposition** dépense = P(conversion) × panier moyen : chez les acheteurs, le panier moyen ne diffère pas (p = 0,97 Hommes, p = 0,51 Femmes ; ≈ 114 $). L'effet passe par le **nombre d'acheteurs**. Mise en garde notée : comparer les acheteurs entre groupes est une comparaison post-traitement, non randomisée (biais de sélection).
- **Comparaisons multiples** : 9 tests (2 e-mails × 3 métriques + Hommes vs Femmes × 3), corrections **Holm** (FWER, retenue) et Benjamini-Hochberg (FDR, montrée) : les 9 restent significatives. Hommes > Femmes nettement sur visite/conversion, **de justesse sur la dépense** (+0,35 $, p = 0,03).
- **Ajustement par covariables** (ANCOVA / logique CUPED, MCO + erreurs standard robustes HC1) : effets inchangés, erreur standard réduite de seulement **0,1 à 1,4 %**, car les covariables prédisent très mal le résultat à 2 semaines (R² ≈ 0,001 pour la dépense ; corrélation `history`↔`spend` = 0,022). Les estimations simples restent la référence.
- **Hétérogénéité (aperçu)** par profil d'achat passé (`figures/02_heterogeneite_profil.png`) : chez les « femmes seulement », les deux e-mails font jeu égal (≈ +0,62 $) ; chez les clients achetant pour hommes, l'e-mail Femmes n'a pas d'effet net, l'e-mail Hommes si (+1,83 $ chez les acheteurs mixtes, IC large). Test d'interaction e-mail Femmes × `mens` : −0,38 $, p = 0,14 (non significatif seul) → motive les modèles d'uplift.

## 3. Analyse de puissance

Notebook : [`notebooks/03_power_analysis.ipynb`](../notebooks/03_power_analysis.ipynb)

**Résultats** (n = 21 306 par groupe, α = 5 % bilatéral, puissance 80 %) :

| Métrique | Niveau contrôle | MDE corrigée | MDE relative | n / groupe pour +10 % |
|---|---|---|---|---|
| Visite | 10,62 % | +0,85 pt | +8 % | ≈ 14 000 |
| Conversion | 0,573 % | +0,22 pt | +39 % | ≈ 290 000 |
| Dépense | 0,653 $ | +0,33 $ | +50 % | ≈ 500 000 |

**Démarche et décisions** :
- Formule de manuel MDE ≈ 2,8 × erreur standard (variances égales, celle du contrôle), vérifiée contre `statsmodels.stats.power.NormalIndPower`.
- **Simulation Monte-Carlo** (20 000 expériences binomiales, graine 42) : 5,3 % de faux positifs sous H₀ (OK), mais seulement **73,8 % de puissance** à la MDE « de manuel » de la conversion au lieu de 80 %. Cause : la variance p(1−p) augmente avec le taux sous traitement, ce qui n'est pas négligeable pour un événement rare.
- **Formule corrigée** (variance sous H₀ avec proportion commune pour le seuil, variance sous H₁ pour la dispersion ; pour la dépense, σ_T² ≈ σ_C² × (1 + lift), vérifié sur les données : 292 prédit contre 315 observé pour Hommes, 222 contre 229 pour Femmes) ; MDE et n résolus numériquement (`scipy.optimize.brentq`). Validée par simulation : 80,6 % de rejets à la MDE corrigée. **C'est la formule utilisée partout ensuite.**
- Coefficients de variation σ/moyenne : 2,9 (visite), 13 (conversion), 18 (dépense) → explique l'écart de MDE entre métriques. Le choix de la métrique principale change le coût d'un test d'un facteur 20 à 35.
- « Puissance observée » montrée avec la mise en garde de Hoenig & Heisey (2001) : transformation de la p-value, pas une information nouvelle. Effet e-mail Femmes sur la dépense = 1,3 × MDE : détectable, sans grande marge.
- **Sous-groupes** : l'interaction e-mail Femmes × `mens` de la section 2 (−0,375 $, erreur std 0,257) n'avait que **31 %** de puissance ; MDE de l'interaction 0,72 $ ; il faudrait ≈ 3,7× plus de clients (≈ 235 000). Le « non significatif » de la section 2 est non concluant.
- Figures : `figures/03_courbes_puissance.png`, `figures/03_taille_echantillon.png`.

**Conséquence pour la section 4** : les effets individuels sont petits face au bruit, donc les modèles d'uplift seront bruités. Il faut les évaluer sur un jeu de test séparé (courbes d'uplift / Qini) et privilégier la conversion (et la visite) comme signal plutôt que la dépense brute.

## 4. Modèles d'uplift

Notebook : [`notebooks/04_uplift_models.ipynb`](../notebooks/04_uplift_models.ipynb)

**Objectif** : estimer l'effet individuel conditionnel τ(x) (CATE) de chaque e-mail, c'est-à-dire trouver les « persuadables », pas les clients qui achèteraient de toute façon.

**Protocole d'évaluation (décisions)** :
- **Cross-fitting en 5 plis** stratifiés (groupe × conversion) : chaque client reçoit une prédiction hors échantillon, et l'évaluation porte sur les 64 000 clients. Un jeu de test à 30 % n'aurait eu que 40 à 80 acheteurs par groupe (cf. section 3).
- **Qini normalisé** = moyenne de (Q(k) − diagonale) / Q(n), avec Q(k) = Y_T(k) − Y_C(k)·N_T(k)/N_C(k) (Radcliffe, 2007). Chaque e-mail est évalué contre le contrôle séparément.
- **Distribution nulle par permutation** (500 classements aléatoires) → p-value empirique. Indispensable : l'écart-type du Qini sous le hasard (≈ 0,04 pour la conversion) est du même ordre que les scores des modèles médiocres.
- Modèles de base : XGBoost peu profond et régularisé (200 arbres, profondeur 3, lr 0,03, `min_child_weight` 20 pour la classification et 50 pour la régression).

**Modèles comparés** (cible : conversion) : modèle de réponse (baseline), S-learner, T-learner (XGBoost et logistique), transformation de cible (Athey & Imbens, 2015), X-learner (Künzel et al., 2019).

**Résultats** :

| Qini conversion (p) | E-mail Hommes | E-mail Femmes |
|---|---|---|
| Modèle de réponse | 0,024 (0,30) | 0,135 (0,06) |
| S-learner XGBoost | 0,006 (0,46) | 0,256 (0,002) |
| **T-learner XGBoost** | −0,014 (0,66) | **0,295 (0,002)** |
| T-learner logistique | −0,038 (0,84) | 0,216 (0,008) |
| Transformation de cible | −0,035 (0,82) | 0,165 (0,02) |
| X-learner | −0,030 (0,77) | 0,156 (0,03) |

- **E-mail Femmes : effet hétérogène, bien capté.** Le T-learner XGBoost cible 45 % des clients et récolte la quasi-totalité de l'effet (`figures/04_courbes_qini.png`). Stable sur 3 graines de découpage (0,295 à 0,316).
- **E-mail Hommes : effet homogène.** Aucun modèle ne bat le hasard. Le diagramme par déciles (`figures/04_uplift_deciles.png`) montre un uplift *prédit* de 1,6 à 0,1 point, mais un uplift *observé* plat : le modèle invente de l'hétérogénéité à partir du bruit.
- **Robustesse** : un T-learner trop régularisé (100 arbres, profondeur 2, feuilles ≥ 100) prédit un uplift quasi constant (écart-type 0,01 pt contre 0,49) et perd tout le signal.
- **Explication** par arbre substitut de profondeur 2 sur l'uplift prédit de l'e-mail Femmes (R² = 0,46), vérifiée sur l'uplift **observé** brut de chaque segment :

  | Segment | Clients | Uplift conv. prédit (Femmes) | Observé Femmes | Observé Hommes |
  |---|---|---|---|---|
  | `history` > 500 $, `recency` ≤ 2 | 3 740 | +1,20 pt | +1,29 pt | +1,15 pt |
  | `history` > 500 $, `recency` > 2 | 4 340 | +0,78 pt | +0,73 pt | +1,12 pt |
  | `history` ≤ 500 $, pas d'achat hommes | 26 083 | +0,44 pt | +0,46 pt | +0,48 pt |
  | `history` ≤ 500 $, achat hommes | 29 837 | +0,02 pt | −0,01 pt | +0,73 pt |

- **Dépense** : uplift de conversion × panier moyen (116,4 $) classe mieux sur la dépense (Qini 0,25 pour Femmes) qu'un T-learner entraîné directement sur `spend` (0,20 ; négatif pour Hommes). C'est l'option retenue pour la section 5.
- Prédictions hors échantillon sauvegardées dans `data/uplift_predictions.csv` (non versionné, régénéré par le notebook).

## 5. Politique de ciblage et ROI

Notebook : [`notebooks/05_targeting_roi.ipynb`](../notebooks/05_targeting_roi.ipynb)

**Hypothèses économiques** (externes au jeu de données, testées en sensibilité) : **marge brute 30 %** du chiffre d'affaires (plage 10-60 %), **coût complet 0,05 $ par e-mail** (envoi + création + coût de désabonnement/fatigue ; plage 0-0,50 $). Profit(π) = marge × E[spend | π] − coût × part contactée.

**Évaluation hors politique** : estimateur stratifié par action (IPW normalisé de Hájek), valide grâce à la randomisation et aux prédictions hors échantillon. Vérifié : il redonne exactement la moyenne du groupe pour une politique uniforme. Intervalles par **bootstrap apparié** (1 000 rééchantillonnages, graine 42 ; prédictions gardées fixes, donc IC légèrement optimistes pour les politiques d'uplift).

**Politiques comparées** (pour 100 000 clients, marge 30 %, coût 0,05 $) :

| Politique | Profit incrémental vs aucun envoi | vs « tous Hommes » |
|---|---|---|
| Tous : e-mail Hommes | **+18 100 $** [9 500 ; 26 500] | — |
| Tous : e-mail Femmes | +7 700 $ [0 ; 15 000] | −10 400 $ [−19 100 ; −500] |
| Uplift naïf (modèles Hommes + Femmes) | +16 800 $ [8 700 ; 24 300] | −1 300 $ [−6 200 ; +4 000] |
| **Hybride** (ATE Hommes + modèle Femmes ; 21 % basculent vers l'e-mail Femmes) | +20 400 $ [10 800 ; 29 100] | +2 300 $ [−1 600 ; +6 700] |

- **L'uplift naïf ne fait pas mieux que l'envoi à tous** : il se fie à l'hétérogénéité inventée du modèle Hommes (section 4). Principe retenu : n'utiliser une estimation individualisée que si elle est validée hors échantillon, sinon la moyenne.
- **Seuil de rentabilité** de l'e-mail Hommes : coût < 0,77 $ × marge (≈ 0,23 $ à 30 %). Au-delà, aucune politique ne bat clairement « personne » : pas de niche rentable trouvée (`figures/05_profit_selon_cout.png`).
- **Sensibilité** marge × coût (`figures/05_sensibilite.png`) : la meilleure politique uniforme est toujours « Hommes à tous » ou « personne », jamais « Femmes ». Le gain de l'hybride se situe entre +800 et +4 600 $ / 100 000 clients quand l'e-mail Hommes est rentable, et devient légèrement négatif près du seuil.
- **Coût de la preuve** : démontrer le gain de l'hybride (+0,077 $ de CA par client) demanderait ≈ 720 000 clients par bras, soit environ 34× un groupe de cette expérience. C'est indémontrable en pratique.

**Recommandation** (pour 100 000 clients) :
1. **Envoyer l'e-mail Hommes à tous** : +77 000 $ de chiffre d'affaires, **+18 100 $ de profit** pour 5 000 $ d'envoi (**ROI ≈ 3,6**). Valable tant que coût/e-mail < 0,77 $ × marge.
2. **Ne pas cibler l'e-mail Hommes** par un modèle d'uplift (effet homogène).
3. **Option** : basculer vers l'e-mail Femmes le client sur cinq jugé plus réceptif par le modèle (gros clients sans historique d'achat hommes). Gain ≈ +2 300 $, non démontré : à n'adopter que si produire deux e-mails ne coûte rien de plus.
4. **Si l'envoi coûte plus que le seuil** (courrier, bon de réduction) : pas de campagne de masse.
5. **Garder un groupe contrôle** (≈ 10 %) dans les prochaines campagnes, et piloter les tests sur la visite.

**Limites** : hypothèses de marge et de coût externes ; effet mesuré sur 2 semaines (long terme inconnu) ; données de 2008 ; politique hybride conçue après analyse des mêmes données (évaluation légèrement optimiste).

## 6. Industrialisation

- **Package `campaignlift/`** : les briques stabilisées des notebooks, un module par étape (`data`, `experiment`, `power`, `uplift`, `policy`).
- **Commande `campaignlift`** : rejoue l'analyse complète pour une marge et un coût d'envoi donnés.
- **Notebooks autonomes** : ils restent indépendants du package, pour exposer chaque calcul de façon explicite.
- **Cohérence garantie par les tests** : `tests/test_reproduction.py` vérifie que le package reproduit les chiffres des notebooks (p du SRM = 0,904, |SMD| max = 0,0137, ATE, MDE, profit +18 095 $ à l'identique ; Qini et gain de l'hybride avec tolérance).
- **Portabilité** : les quantités issues de XGBoost varient légèrement selon la plateforme, à cause des arrondis flottants en calcul multithread. Le Qini de l'e-mail Femmes vaut 0,295 sous Windows et 0,290 sous Linux, et le gain de l'hybride 2 305 $ contre 1 952 $. Ces écarts restent dans les intervalles de confiance et ne changent aucune conclusion. Les tests de reproduction vérifient donc ces quantités avec une tolérance, et les autres à l'identique.
- **Tests unitaires sur données synthétiques** :
  - z-test identique à `statsmodels` ;
  - bootstrap cohérent avec Welch ;
  - formule de puissance corrigée validée par simulation ;
  - Qini d'un oracle positif et d'un classement aléatoire ≈ 0 ;
  - estimateur de politique sans biais sur des résultats potentiels connus.
