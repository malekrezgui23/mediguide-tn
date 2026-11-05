"""Fonctions communes aux scripts de données : lecture du CSV, slug, normalisation des dosages."""

import csv
import re
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
BRUT = RACINE / "donnees" / "brut"

# Ramène chaque unité à une unité de base : 1 g = 1000 mg, 1 mcg = 1 µg…
UNITES = {"g": ("mg", 1000), "gr": ("mg", 1000), "mg": ("mg", 1), "mcg": ("µg", 1), "µg": ("µg", 1),
          "ug": ("µg", 1), "ml": ("ml", 1), "l": ("ml", 1000), "ui": ("ui", 1), "%": ("%", 1)}
DOSE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(mcg|µg|ug|mg|gr|g|ml|l|ui|%)(?![a-zà-ÿ])", re.IGNORECASE)


def lire_amm() -> list[dict]:
    with open(BRUT / "liste_amm.csv", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def slug(texte: str) -> str:
    """« Ben Arous » -> « ben-arous » : minuscules, sans accents, avec des tirets."""
    texte = unicodedata.normalize("NFKD", texte.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texte).strip("-")


def doses(texte: str) -> list[str]:
    """« 1 g/5 ML » -> ['1000mg', '5ml'] : les doses d'un texte, dans une écriture unique."""
    resultat = []
    for nombre, unite in DOSE.findall(texte.replace("µ", "µ").lower()):
        base, facteur = UNITES[unite]
        valeur = float(nombre.replace(",", ".")) * facteur
        resultat.append(f"{valeur:g}{base}")
    return resultat


def normaliser_dosage(texte: str) -> str:
    """Écriture unique d'un dosage. Sans dose reconnue : le texte en minuscules, sans espaces."""
    trouvees = doses(texte)
    return "/".join(trouvees) if trouvees else re.sub(r"\s+", "", texte.lower())


def substances(dci: str) -> list[str]:
    """« PARACETAMOL+CODEINE » -> ['PARACETAMOL', 'CODEINE']."""
    return [s.strip() for s in dci.split("+") if s.strip()]


def code_composition(dci: str) -> str:
    """Les substances triées : « B+A » et « A+B » donnent le même code."""
    return "+".join(sorted(slug(s) for s in substances(dci)))
