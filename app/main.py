"""Web service REST de MédiGuide TN : 6 endpoints qui renvoient en JSON les résultats des requêtes SPARQL.

Commande : uvicorn app.main:app   puis ouvrir http://127.0.0.1:8000/docs
Réponses : {"inference": bool, "nombre": int, "resultats": [...]} ; paramètre inference=true|false partout.
"""

import re
from typing import Literal as Choix

from fastapi import FastAPI, HTTPException, Query
from rdflib import Namespace
from rdflib.namespace import RDF

from app.requetes import executer, graphe
from scripts.outils import slug

MED = Namespace("http://mediguide-tn.org/vocab#")
MEDD = Namespace("http://mediguide-tn.org/donnees/")
ORIGINES = {"tunisien": MED.LaboratoireTunisien, "etranger": MED.LaboratoireEtranger}
TYPES = {"generique": MED.Generique, "biosimilaire": MED.Biosimilaire, "princeps": MED.Princeps,
         "copie": MED.MedicamentCopie}
INFERENCE = Query(True, description="true : graphe avec les triplets déduits par R1 et R2 ; false : données brutes")

app = FastAPI(title="MédiGuide TN",
              description="Guide des médicaments et génériques en Tunisie : un graphe de connaissances interrogé en "
                          "SPARQL. Les prix sont ceux de la liste PCT (originePrix = reel) ou estimés "
                          "(originePrix = estime). Ce guide ne remplace pas l'avis d'un médecin ou d'un pharmacien.")
graphe(True), graphe(False)  # chargés au démarrage : chaque appel est ensuite plus rapide


def reponse(inference: bool, resultats: list) -> dict:
    return {"inference": inference, "nombre": len(resultats), "resultats": resultats}


def verifier_existe(uri, classe, inference: bool, message: str, valeur: str):
    """404 clair plutôt qu'une liste vide quand l'identifiant n'existe pas (ces types sont écrits dans les données)."""
    if (uri, RDF.type, classe) not in graphe(inference):
        raise HTTPException(404, f"{message} : {valeur}")


def prix_par_unite(prix: float, presentation: str | None) -> float | None:
    """Prix d'une unité si la boîte en indique le nombre (« B/30 », « B/12 Sachets ») ; sinon None (« FL/100 ML »)."""
    trouve = re.fullmatch(r"(?i)\s*(?:b|fl)\s*/\s*(\d+)\s*([a-zé]*)\s*", presentation or "")
    if not trouve or int(trouve.group(1)) == 0 or trouve.group(2).lower() in {"ml", "l", "g", "gr", "mg"}:
        return None
    return prix / int(trouve.group(1))


def economie_pct(reference: dict, r: dict) -> float | None:
    """Économie en % par unité : on ne compare pas une boîte de 10 à une boîte de 30.
    None si le nombre d'unités d'une des deux boîtes n'est pas lisible (flacon, tube…) et que les présentations diffèrent."""
    avant = prix_par_unite(reference["prixReference"], reference["presentationReference"])
    apres = prix_par_unite(r["prix"], r["presentation"])
    if avant is None or apres is None:
        if r["presentation"] != reference["presentationReference"]:
            return None
        avant, apres = reference["prixReference"], r["prix"]
    return round(100 * (avant - apres) / avant)


@app.get("/medicaments", summary="Médicaments d'une substance, filtrés, du moins cher au plus cher (Q2)")
def medicaments(substance: str = Query(..., description="ex. paracetamol"),
                forme: str | None = Query(None, description="ex. comprime"),
                origine: Choix["tunisien", "etranger"] | None = Query(None, description="origine du laboratoire"),
                type: Choix["generique", "biosimilaire", "princeps", "copie"] | None = Query(
                    None, description="copie = générique ou biosimilaire (déduit par R1)"),
                limite: int = Query(50, ge=1, le=500, description="nombre de résultats (1 à 500)"),
                inference: bool = INFERENCE):
    uri_substance = MEDD[f"substance-{slug(substance)}"]
    verifier_existe(uri_substance, MED.SubstanceActive, inference, "Substance inconnue", substance)
    uri_forme = MEDD[f"forme-{slug(forme)}"] if forme else None
    if forme:
        verifier_existe(uri_forme, MED.Forme, inference, "Forme inconnue", forme)
    parametres = {"substance": uri_substance, "forme": uri_forme,
                  "origine": ORIGINES[origine] if origine else None, "type": TYPES[type] if type else None}
    return reponse(inference, executer("q2", parametres, inference)[:limite])


@app.get("/medicaments/{amm}/equivalents", summary="Équivalents d'un médicament, prix, économie et stock (Q5)")
def equivalents(amm: str,
                pharmacie: str = Query("demo", description="pharmacie dont on regarde le stock"),
                origine: Choix["tunisien", "etranger"] | None = Query(None, description="origine du laboratoire"),
                en_stock: bool = Query(False, description="true : seulement ce que la pharmacie a en stock"),
                inference: bool = INFERENCE):
    medicament = MEDD[f"medicament-{slug(amm)}"]
    # Q5 renverrait une liste vide pour une AMM inconnue : on vérifie qu'elle existe avant
    if (medicament, MED.fabriquePar, None) not in graphe(inference):
        raise HTTPException(404, f"Médicament inconnu : AMM {amm}")
    uri_pharmacie = MEDD[f"pharmacie-{slug(pharmacie)}"]
    verifier_existe(uri_pharmacie, MED.Pharmacie, inference, "Pharmacie inconnue", pharmacie)

    resultats = executer("q5", {"medicament": medicament, "pharmacie": uri_pharmacie}, inference)
    for r in resultats:
        r["enStock"] = bool(r["enStock"])
        r["economiePct"] = economie_pct(r, r)
    if origine:
        attendu = {"tunisien": "LaboratoireTunisien", "etranger": "LaboratoireEtranger"}[origine]
        resultats = [r for r in resultats if r["origine"] == attendu]
    if en_stock:
        resultats = [r for r in resultats if r["enStock"]]
    return reponse(inference, resultats)


@app.get("/substances/top", summary="Substances qui ont le plus de médicaments (Q1)")
def substances_top(limite: int = Query(10, ge=1, le=100, description="nombre de substances (1 à 100)"),
                   inference: bool = INFERENCE):
    # LIMIT n'accepte pas de variable en SPARQL : on coupe ici
    return reponse(inference, executer("q1", {}, inference)[:limite])


@app.get("/substances/source-unique", summary="Substances d'un médicament vital qui dépendent d'un seul laboratoire (Q4)")
def substances_source_unique(inference: bool = INFERENCE):
    return reponse(inference, executer("q4", {}, inference))


@app.get("/sous-classes/dependance-etranger", summary="Sous-classes sans aucun laboratoire tunisien (Q3)")
def sous_classes_dependance(inference: bool = INFERENCE):
    return reponse(inference, executer("q3", {}, inference))


@app.get("/statistiques/inference", summary="Ce que l'inférence ajoute (Q0 et taille du graphe)")
def statistiques(inference: bool = INFERENCE):
    resultats = [
        {"indicateur": "médicaments de type med:Medicament (Q0)", "valeur": executer("q0", {}, inference)[0]["nbMedicaments"]},
        {"indicateur": "triplets dans le graphe", "valeur": len(graphe(inference))},
    ]
    if inference:
        resultats.append({"indicateur": "triplets déduits par R1 et R2", "valeur": len(graphe(True)) - len(graphe(False))})
    return reponse(inference, resultats)
