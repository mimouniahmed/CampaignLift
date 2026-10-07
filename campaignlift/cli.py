"""Rejoue l'analyse complète et affiche la recommandation : `campaignlift --marge 0.3 --cout 0.05`."""

import argparse

import numpy as np

from . import experiment, policy, power, uplift
from .data import (CHEMIN_PAR_DEFAUT, CONTROLE, charger, codes_traitement, matrice_covariables,
                   panier_moyen, resultats)


def fmt(x, decimales=0):
    return f"{x:,.{decimales}f}".replace(",", " ")


def section(titre):
    print(f"\n=== {titre} ===")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="campaignlift", description=__doc__)
    parser.add_argument("--donnees", default=str(CHEMIN_PAR_DEFAUT), help="chemin du CSV Hillstrom (téléchargé s'il manque)")
    parser.add_argument("--marge", type=float, default=0.30, help="marge brute sur le chiffre d'affaires (défaut 0.30)")
    parser.add_argument("--cout", type=float, default=0.05, help="coût complet par e-mail envoyé en $ (défaut 0.05)")
    parser.add_argument("--base", type=int, default=100_000, help="taille de base pour exprimer les gains (défaut 100 000)")
    parser.add_argument("--n-boot", type=int, default=300, help="rééchantillonnages bootstrap pour les politiques (défaut 300)")
    parser.add_argument("--permutations", type=int, default=200, help="permutations pour le test du Qini (défaut 200)")
    args = parser.parse_args(argv)

    df = charger(args.donnees)
    W, Y, X = codes_traitement(df), resultats(df), matrice_covariables(df)

    section("1. Randomisation")
    srm = experiment.test_sample_ratio(df["segment"])
    smd_max = experiment.equilibre_covariables(df).abs().max().max()
    print(f"Effectifs : {srm['effectifs']}")
    print(f"Sample ratio mismatch : χ² = {srm['chi2']:.3f}, p = {srm['p_value']:.3f}   |   |SMD| max = {smd_max:.4f}")

    section("2. Effets moyens (vs aucun e-mail)")
    for _, r in experiment.effets_moyens(df).iterrows():
        echelle, unite = (1, " $") if r["metrique"] == "spend" else (100, " pt")
        print(f"{r['traitement']:<14} {r['metrique']:<10} {r['difference'] * echelle:+.3f}{unite}  "
              f"IC95 [{r['ic95_bas'] * echelle:+.3f} ; {r['ic95_haut'] * echelle:+.3f}]  p = {r['p_value']:.1e}")

    section("3. Puissance (MDE à 80 %, α = 5 %)")
    controle = df[df["segment"] == CONTROLE]
    n = len(controle)
    for m in ["visit", "conversion", "spend"]:
        d = power.mde(controle[m], n, binaire=(m != "spend"))
        print(f"{m:<10} MDE = {d:.4f}  ({d / controle[m].mean():+.0%} relatif)")

    section("4. Uplift (T-learner XGBoost, cross-fitting 5 plis)")
    P = uplift.t_learner(X, W, Y["conversion"])
    for g, nom in [(1, "Mens E-Mail"), (2, "Womens E-Mail")]:
        u = P[:, g] - P[:, 0]
        score = uplift.evaluer(u, Y["conversion"], W, g)
        p = uplift.p_value_permutation(score, Y["conversion"], W, g, n_permutations=args.permutations)
        print(f"{nom:<14} Qini normalisé (conversion) = {score:+.3f}   p permutation = {p:.3f}")

    section(f"5. Politiques (marge {args.marge:.0%}, coût {args.cout:.2f} $ par e-mail, pour {fmt(args.base)} clients)")
    panier = panier_moyen(df)
    ate_hommes = Y["spend"][W == 1].mean() - Y["spend"][W == 0].mean()
    pols = policy.politiques((P[:, 1] - P[:, 0]) * panier, (P[:, 2] - P[:, 0]) * panier, ate_hommes, args.marge, args.cout)
    comparaison = policy.comparer(pols, W, Y["spend"], args.marge, args.cout, n_boot=args.n_boot)
    for nom, r in comparaison.iterrows():
        print(f"{nom:<40} vs personne {fmt(r['vs_personne'] * args.base):>8} $ "
              f"[{fmt(r['vs_personne_bas'] * args.base)} ; {fmt(r['vs_personne_haut'] * args.base)}]   "
              f"vs tous Hommes {fmt(r['vs_tous_hommes'] * args.base):>7} $")

    section("Recommandation")
    seuil = args.marge * ate_hommes
    if args.cout < seuil:
        gain = comparaison.loc["tous : e-mail Hommes", "vs_personne"]
        print(f"Envoyer l'e-mail Hommes à tous : profit incrémental ≈ {fmt(gain * args.base)} $ pour {fmt(args.base)} clients"
              + (f", ROI ≈ {gain / args.cout:.1f}." if args.cout > 0 else "."))
        print(f"Rentable tant que le coût par e-mail reste sous {seuil:.3f} $ (= {ate_hommes:.2f} $ × marge).")
        hyb = comparaison.loc["hybride (Hommes moyen + modèle Femmes)"]
        print(f"Option hybride (e-mail Femmes pour {hyb['part_femmes']:.0%} des clients) : {fmt(hyb['vs_tous_hommes'] * args.base)} $ "
              f"de plus, IC95 [{fmt(hyb['vs_tous_hommes_bas'] * args.base)} ; {fmt(hyb['vs_tous_hommes_haut'] * args.base)}] : non démontré.")
    else:
        print(f"Coût par e-mail ({args.cout:.2f} $) au-dessus du seuil de rentabilité ({seuil:.3f} $) : pas de campagne de masse.")


if __name__ == "__main__":
    main()
