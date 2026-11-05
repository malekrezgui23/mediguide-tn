"""Fusionne les prix PCT réels avec la liste des AMM, et estime les prix manquants.

Commande : python scripts/completer_donnees.py
Entrées  : donnees/brut/liste_amm.csv, donnees/brut/prix_medicaments_pct_07-2026_complet.csv (jamais modifiés)
Sortie   : donnees/brut/liste_amm_complete.csv, avec trois colonnes ajoutées :
           prix_public, origine_prix (reel | estime), methode_prix
           origine (reel = rien d'ajouté sauf le prix PCT ; complete = prix estimé)

Un prix réel n'est retenu que si le nom, les doses, le nombre d'unités et la forme concordent.
Un prix estimé part toujours du prix réel le plus proche, du plus fiable au moins fiable :
  1. même nom et même dose, autre taille de boîte
  2. équivalent exact (même composition, dose et forme)
  3. même composition, autre dose
  4. valeur de repère de la substance, pour les substances les plus courantes (comprimés, gélules…)
  5. médiane du prix par unité de la sous-classe
  6. valeur de repère de la classe, sinon médiane de la classe
Les médianes séparent les boîtes d'unités (B/30) des contenants uniques (flacon, tube).
Ces règles rendent les génériques moins chers : les économies sur des prix estimés sont des illustrations.
"""

import csv
import hashlib
import re
from collections import defaultdict
from statistics import median

from outils import BRUT, RACINE, code_composition, doses, lire_amm, normaliser_dosage, slug

FICHIER_PRIX = BRUT / "prix_medicaments_pct_07-2026_complet.csv"
PRIX_RONDS = {5.0, 10.0}  # 52 lignes PCT à ces valeurs : gardées telles quelles, mais pas prises comme référence

# Écart de prix selon le type, par rapport à un princeps
FACTEUR_TYPE = {"Princeps": 1.0, "Générique": 0.70, "Biosimilaire": 0.75}
FACTEUR_TUNISIEN = 0.90  # un générique fabriqué en Tunisie, par rapport à un générique importé
FACTEUR_FORME = {"injectable": 2.5, "autre": 1.0}
PRIX_MINIMUM, PRIX_MAXIMUM = 1.5, 5000.0
# Prix par unité (DT) pour les classes coûteuses, trop peu présentes dans la liste PCT
REPERE_CLASSE = {"ANTINEOPLASIQUES ET IMMUNOMODULATEURS": 60.0, "ANTIINFECTIEUX GENERAUX A USAGE SYSTEMIQUE": 2.0,
                 "SANG ET ORGANES HEMATOPOIETIQUES": 8.0}
# Prix par unité d'un princeps (DT), ordre de grandeur donné par l'IA, pour les substances courantes
REPERE_SUBSTANCE = {
    "paracetamol": 0.30, "ibuprofene": 0.25, "diclofenac": 0.30, "acide-acetylsalicylique": 0.15,
    "amoxicilline": 0.50, "acide-clavulanique+amoxicilline": 1.00, "azithromycine": 3.00, "ciprofloxacine": 1.20,
    "metformine": 0.15, "glimepiride": 0.40, "atorvastatine": 1.00, "rosuvastatine": 1.20, "simvastatine": 0.60,
    "amlodipine": 0.60, "bisoprolol": 0.50, "omeprazole": 0.60, "esomeprazole": 0.80, "pantoprazole": 0.80,
    "pregabaline": 1.20, "losartan": 0.70, "valsartan": 0.80, "irbesartan": 0.80, "enalapril": 0.40,
    "captopril": 0.30, "furosemide": 0.20, "levothyroxine": 0.10,
}
FAMILLES = {"comp": "comprime", "gél": "gelule", "gel.": "gelule", "gelule": "gelule", "caps": "capsule",
            "inj": "injectable", "collyre": "collyre", "sirop": "sirop", "suppo": "suppositoire",
            "crème": "creme", "creme": "creme", "aérosol": "inhalation", "inhal": "inhalation"}


def famille_forme(texte: str) -> str | None:
    texte = texte.lower()
    return next((f for mot, f in FAMILLES.items() if mot in texte), None)


def nombres(texte: str) -> set[int]:
    return {int(n) for n in re.findall(r"\d+", texte)}


def unites_boite(presentation: str) -> int:
    """« B/30 » -> 30, « FL/28 » -> 28, « B/5/5ML » -> 5 ; « FL/100ML » ou illisible -> 1."""
    trouve = re.match(r"(?i)\s*(?:b|c|bt|boite|fl|p|pilulier)\s*/\s*(\d+)\s*([a-zµ]*)", presentation)
    if not trouve or trouve.group(2).lower() in {"ml", "l", "g", "gr", "mg"}:
        return 1
    return max(int(trouve.group(1)), 1)


def groupe(ligne: dict) -> str:
    return "boite" if unites_boite(ligne["Présentation"]) > 1 else "unique"


def lire_laboratoires_tunisiens() -> set[str]:
    with open(RACINE / "donnees" / "laboratoires.csv", encoding="utf-8", newline="") as f:
        return {l["slug"] for l in csv.DictReader(f) if l["implantation"] == "tunisie"}


TUNISIENS = lire_laboratoires_tunisiens()


def facteur_type(ligne: dict) -> float:
    facteur = FACTEUR_TYPE[ligne["G/P/B"].strip()]
    if ligne["G/P/B"].strip() != "Princeps" and slug(ligne["Laboratoire"]) in TUNISIENS:
        facteur *= FACTEUR_TUNISIEN
    return facteur


def lire_prix() -> list[dict]:
    with open(FICHIER_PRIX, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def concordent(ligne: dict, reste: str) -> bool:
    """Le reste du libellé PCT (après le nom) décrit-il bien cette ligne AMM ?"""
    doses_amm, doses_pct = set(doses(ligne["Dosage"])), set(doses(reste))
    if doses_amm and not doses_amm <= doses_pct:
        return False
    # Principes actifs identiques : « MICARDIS 80 mg » n'est pas « MICARDIS PLUS 80mg/12.5mg »
    actifs = lambda d: {x for x in d if x.endswith(("mg", "µg", "ui"))}  # noqa: E731
    avant_boite = re.split(r"(?i)\b(?:bt|fl|tb|b/|ser)\b", reste)[0]  # « Tb/30gr » décrit le tube, pas la dose
    if actifs(doses_amm) != actifs(doses(avant_boite)) and (doses_amm or re.search(r"(?i)\bplus\b|\bfort\b", reste)):
        return False
    conditionnement = re.split(r"(?i)\b(?:bt|fl|tb|b/|ser)\b", reste)[-1]
    n_pct, n_amm = nombres(conditionnement), nombres(ligne["Présentation"])
    if n_pct and n_amm and not n_pct & n_amm:
        return False
    f_pct, f_amm = famille_forme(reste), famille_forme(ligne["Forme"])
    return not (f_pct and f_amm and f_pct != f_amm)


def rapprocher(lignes: list[dict], prix_pct: list[dict]) -> dict[str, tuple[float, str]]:
    """{AMM: (prix, référence PCT)} pour les concordances. Le nom le plus long gagne (LYRICA avant LYRICA 75…)."""
    par_nom = defaultdict(list)
    for l in lignes:
        par_nom[slug(l["Nom"])].append(l)
    noms = sorted(par_nom, key=len, reverse=True)
    trouves = {}
    for p in prix_pct:
        s = slug(p["medicament"])
        for nom in noms:
            if s.startswith(nom + "-") or s == nom:
                reste = p["medicament"][len(nom):]
                for l in par_nom[nom]:
                    if concordent(l, reste):
                        trouves.setdefault(l["AMM"].strip(), (float(p["prix_public_ttc_dt"]), p["reference"]))
                break
    return trouves


def variation(amm: str) -> float:
    """Écart de ±8 %, toujours le même pour une AMM donnée : deux lancements donnent le même fichier."""
    return 0.92 + int(hashlib.sha256(amm.encode()).hexdigest()[:8], 16) % 1600 / 10000


def forme_prix(ligne: dict) -> str:
    return "injectable" if "inj" in ligne["Forme"].lower() or "perfusion" in ligne["Forme"].lower() else "autre"


def prix_unitaire(ligne: dict, prix: float) -> float:
    """Prix ramené à une unité et au prix d'un princeps."""
    return prix / unites_boite(ligne["Présentation"]) ** 0.85 / facteur_type(ligne)


def estimer(lignes: list[dict], reels: dict) -> dict[str, tuple[float, str]]:
    meme_nom, equivalents, composition, sous_classe, classe = (defaultdict(list) for _ in range(5))
    for l in lignes:
        amm = l["AMM"].strip()
        if amm not in reels or reels[amm][0] in PRIX_RONDS:
            continue
        pu = prix_unitaire(l, reels[amm][0])
        comp, dose = code_composition(l["DCI"]), normaliser_dosage(l["Dosage"])
        meme_nom[(slug(l["Nom"]), dose, groupe(l))].append(pu)
        equivalents[(comp, dose, slug(l["Forme"]), groupe(l))].append(pu)
        composition[(comp, groupe(l))].append(pu)
        sous_classe[(l["Sous Classe"].strip(), groupe(l))].append(pu / FACTEUR_FORME[forme_prix(l)])
        classe[(l["Classe"].strip(), groupe(l))].append(pu / FACTEUR_FORME[forme_prix(l)])

    estimes = {}
    mediane_generale = median(v for vs in classe.values() for v in vs)
    for l in lignes:
        amm = l["AMM"].strip()
        if amm in reels or amm in estimes:
            continue
        comp, dose = code_composition(l["DCI"]), normaliser_dosage(l["Dosage"])
        cle_nom, cle_eq = (slug(l["Nom"]), dose, groupe(l)), (comp, dose, slug(l["Forme"]), groupe(l))
        forme = FACTEUR_FORME[forme_prix(l)]
        if cle_nom in meme_nom:
            base, methode = median(meme_nom[cle_nom]), "1-meme-nom"
        elif cle_eq in equivalents:
            base, methode = median(equivalents[cle_eq]), "2-equivalent"
        elif (comp, groupe(l)) in composition:
            base, methode = median(composition[(comp, groupe(l))]), "3-composition"
        elif comp in REPERE_SUBSTANCE and groupe(l) == "boite":
            base, methode = REPERE_SUBSTANCE[comp] * forme, "4-repere-substance"
        elif len(sous_classe.get((l["Sous Classe"].strip(), groupe(l)), [])) >= 3:
            base, methode = median(sous_classe[(l["Sous Classe"].strip(), groupe(l))]) * forme, "5-sous-classe"
        elif l["Classe"].strip() in REPERE_CLASSE:
            base, methode = REPERE_CLASSE[l["Classe"].strip()] * forme, "6-repere-classe"
        else:
            valeurs = classe.get((l["Classe"].strip(), groupe(l))) or [mediane_generale]
            base, methode = median(valeurs) * forme, "6-classe"
        prix = base * unites_boite(l["Présentation"]) ** 0.85 * facteur_type(l) * variation(amm)
        estimes[amm] = (round(min(max(prix, PRIX_MINIMUM), PRIX_MAXIMUM), 3), methode)
    return estimes


def main():
    lignes = lire_amm()
    prix_pct = lire_prix()
    reels = rapprocher(lignes, prix_pct)
    estimes = estimer(lignes, reels)

    colonnes = list(lignes[0].keys()) + ["prix_public", "origine_prix", "methode_prix", "origine"]
    with open(BRUT / "liste_amm_complete.csv", "w", encoding="utf-8", newline="") as f:
        ecrivain = csv.DictWriter(f, fieldnames=colonnes)
        ecrivain.writeheader()
        for l in lignes:
            amm = l["AMM"].strip()
            if amm in reels:
                ajout = {"prix_public": f"{reels[amm][0]:.3f}", "origine_prix": "reel",
                         "methode_prix": f"pct-{reels[amm][1]}", "origine": "reel"}
            else:
                ajout = {"prix_public": f"{estimes[amm][0]:.3f}", "origine_prix": "estime",
                         "methode_prix": estimes[amm][1], "origine": "complete"}
            ecrivain.writerow({**l, **ajout})

    methodes = defaultdict(int)
    for _, m in estimes.values():
        methodes[m] += 1
    references = {r for _, r in reels.values()}
    print(f"{len(lignes)} lignes, {len(reels) + len(estimes)} AMM distinctes")
    print(f"Prix réels : {len(reels)} AMM, à partir de {len(references)} des {len(prix_pct)} lignes PCT")
    print(f"Prix estimés : {len(estimes)} AMM : {dict(sorted(methodes.items()))}")
    for origine in ("reel", "complete", "genere"):
        n = sum((l["AMM"].strip() in reels) == (origine == "reel") for l in lignes) if origine != "genere" else 0
        print(f"  origine = {origine} : {n} lignes")
    non_rapprochees = [p["medicament"] for p in prix_pct if p["reference"] not in references]
    print(f"Lignes PCT non rapprochées : {len(non_rapprochees)}, ex. {non_rapprochees[:12]}")


if __name__ == "__main__":
    main()
