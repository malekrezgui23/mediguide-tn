"""Audit des deux CSV bruts : lignes, valeurs vides, doublons, formats.

Commande : python scripts/auditer_donnees.py
"""

import csv
import re
from collections import Counter
from pathlib import Path

BRUT = Path(__file__).resolve().parent.parent / "donnees" / "brut"


def lire(nom: str) -> list[dict]:
    with open(BRUT / nom, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def auditer_amm():
    lignes = lire("liste_amm.csv")
    print(f"liste_amm.csv : {len(lignes)} lignes, {len({l['AMM'].strip() for l in lignes})} numéros d'AMM distincts")
    print("  Valeurs vides :", {c: n for c in lignes[0] if (n := sum(not (l[c] or "").strip() for l in lignes))})
    amm = Counter(l["AMM"].strip() for l in lignes)
    doublons = [a for a, n in amm.items() if n > 1]
    identiques = sum(len({tuple(l.values()) for l in lignes if l["AMM"].strip() == a}) == 1 for a in doublons)
    print(f"  AMM en double : {len(doublons)}, dont {identiques} lignes strictement identiques")
    sous_classes = {a: {l["Sous Classe"] for l in lignes if l["AMM"].strip() == a} for a in doublons}
    print(f"  AMM en double avec plusieurs sous-classes : {sum(len(s) > 1 for s in sous_classes.values())}")
    dates = sum(not re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", l["Date AMM"].strip()) for l in lignes)
    print(f"  Dates hors format M/J/AAAA : {dates}")
    print("  Colonnes prix ou pays : aucune")


def auditer_prix():
    lignes = lire("prix_medicaments_pct_07-2026_complet.csv")
    prix = [float(l["prix_public_ttc_dt"]) for l in lignes]
    print(f"prix PCT : {len(lignes)} lignes, de {min(prix)} à {max(prix)} DT")
    print(f"  Références en double : {sum(n > 1 for n in Counter(l['reference'] for l in lignes).values())}")
    incoherents = sum(not float(l["prix_gros_ttc_dt"]) <= float(l["prix_pharmacie_ttc_dt"]) <= float(l["prix_public_ttc_dt"])
                      for l in lignes)
    print(f"  Lignes où gros <= pharmacie <= public est faux : {incoherents}")
    ronds = sum(l["prix_public_ttc_dt"] in ("5.000", "10.000") for l in lignes)
    print(f"  Prix publics pile à 5.000 ou 10.000 DT : {ronds} (à vérifier : forfaits ?)")


if __name__ == "__main__":
    auditer_amm()
    auditer_prix()
