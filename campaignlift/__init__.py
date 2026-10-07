"""CampaignLift : analyse d'une expérience marketing randomisée (Hillstrom, 64 000 clients).

Modules :
- data : chargement du jeu de données et matrice des covariables
- experiment : contrôles de randomisation et tests de l'effet moyen
- power : puissance, MDE et taille d'échantillon (formules corrigées)
- uplift : méta-apprenants (T-learner) en cross-fitting et évaluation Qini
- policy : évaluation hors politique, profit et comparaison de politiques
"""

__version__ = "1.0.0"
