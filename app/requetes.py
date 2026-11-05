"""Exécution des requêtes SPARQL de requetes/ : paramètres liés par initBindings, résultats en valeurs simples."""

from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from rdflib import Graph, Literal, URIRef

from app.graphe import FICHIERS, RACINE, charger_graphe

DOSSIER = Path(__file__).resolve().parent.parent / "requetes"
DONNEES = "http://mediguide-tn.org/donnees/"


def graphe(inference: bool) -> Graph:
    """Graphe en mémoire, rechargé seulement si un fichier .ttl a changé (ex. données régénérées)."""
    version = tuple((RACINE / f).stat().st_mtime for f in FICHIERS)
    return _graphe(inference, version)


@lru_cache(maxsize=2)  # une version avec inférence, une sans
def _graphe(inference: bool, version: tuple) -> Graph:
    return charger_graphe(inference)


def simplifier(valeur):
    """URI de nos données -> identifiant court (medd:substance-paracetamol -> paracetamol) ; littéral -> valeur Python."""
    if isinstance(valeur, URIRef):
        texte = str(valeur)
        return texte[len(DONNEES):].split("-", 1)[1] if texte.startswith(DONNEES) else texte.rsplit("#", 1)[-1]
    if isinstance(valeur, Literal):
        python = valeur.toPython()
        return float(python) if isinstance(python, Decimal) else python  # JSON propre : 4.35, pas "4.350"
    return valeur


def executer(nom_requete: str, parametres: dict, inference: bool) -> list[dict]:
    """Lance requetes/<nom_requete>*.rq ; les paramètres (URI ou littéraux rdflib) passent par initBindings,
    jamais collés dans le texte de la requête (pas d'injection SPARQL)."""
    fichier = next(DOSSIER.glob(f"{nom_requete}_*.rq"))
    resultats = graphe(inference).query(fichier.read_text(encoding="utf-8"),
                                        initBindings={k: v for k, v in parametres.items() if v is not None})
    return [{str(var): simplifier(ligne[var]) for var in resultats.vars} for ligne in resultats]
