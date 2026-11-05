"""Écrit donnees/laboratoires.csv : l'origine de chaque laboratoire (colonne absente du CSV AMM).

Classement fait par l'IA, sans source officielle (colonne origine = genere).
fiabilite = a_verifier quand l'IA n'est pas sûre du pays ; tous les autres laboratoires non listés
sont classés étrangers.

Commande : python scripts/classer_laboratoires.py
"""

import csv
from pathlib import Path

from outils import lire_amm, slug

RACINE = Path(__file__).resolve().parent.parent

# Implantation en Tunisie connue, filiales de groupes étrangers comprises
TUNISIENS_SURS = {
    "TERIAK", "SAIPH", "LES LABORATOIRES MEDIS", "ADWYA", "OPALIA PHARMA", "UNIMED", "SIPHAT", "GALPHARMA",
    "PHARMAGHREB", "DAR-ESSAYDALI.", "TAHA PHARMA", "IBN AL BAYTAR", "NEAPOLIS PHARMA", "THERA", "PHARMADERM",
    "CYTOPHARMA", "STERIPHARM", "ADHE-ELS.", "SIMED", "SANOFI AVENTIS PHARMA TUNISIE", "WINTHROP PHARMA TUNISIE",
    "PFIZER  TUNISIE", "PIERRE FABRE MEDICAMENT PRODUCTION TUNISIE", "INSTITUT PASTEUR DE TUNIS",
}
TUNISIENS_A_VERIFIER = {
    "PHILADELPHIA PHARMA", "IPS (Industrie Pharmaceutique Said)", "DORCAS", "MEDICEF", "ALLIANCE PHARMA",
    "ACT PHARMA", "ADVANS PHARMA", "LINO PHARMA", "ALEPT", "MID PHARMA", "CLS PHARMA",
}
ETRANGERS_A_VERIFIER = {"PHARMACARE", "WEST PHARMA", "INFOMED  Pharma", "APM", "DESMA Pharma SARL", "SISORA"}


def main():
    laboratoires = {}
    for ligne in lire_amm():
        nom = ligne["Laboratoire"].strip()
        laboratoires.setdefault(slug(nom), nom)  # « BAYER AG » et « BAYER AG... » : un seul laboratoire

    connus = TUNISIENS_SURS | TUNISIENS_A_VERIFIER | ETRANGERS_A_VERIFIER
    absents = connus - set(laboratoires.values())
    assert not absents, f"Noms absents du CSV : {absents}"

    lignes = []
    for s, nom in sorted(laboratoires.items()):
        tunisien = nom in TUNISIENS_SURS or nom in TUNISIENS_A_VERIFIER
        fiabilite = "a_verifier" if nom in TUNISIENS_A_VERIFIER | ETRANGERS_A_VERIFIER else "sur"
        lignes.append({"slug": s, "nom": nom, "implantation": "tunisie" if tunisien else "etranger",
                       "fiabilite": fiabilite, "origine": "genere"})

    with open(RACINE / "donnees" / "laboratoires.csv", "w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=lignes[0].keys())
        ecrivain.writeheader()
        ecrivain.writerows(lignes)

    nb_tn = sum(l["implantation"] == "tunisie" for l in lignes)
    nb_verif = sum(l["fiabilite"] == "a_verifier" for l in lignes)
    print(f"{len(lignes)} laboratoires : {nb_tn} tunisiens, {len(lignes) - nb_tn} étrangers, {nb_verif} à vérifier")


if __name__ == "__main__":
    main()
