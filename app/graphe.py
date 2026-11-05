"""Chargement du graphe pour le web service (contrat 3 de PLAN.md)."""

from pathlib import Path

from rdflib import Graph

from inference.inferer import appliquer_inference

RACINE = Path(__file__).resolve().parent.parent
FICHIERS = ("ontologie/vocabulaire.ttl", "donnees/medicaments.ttl", "donnees/pharmacies.ttl")


def charger_graphe(inference: bool) -> Graph:
    """Vocabulaire + médicaments + pharmacie ; si inference=True, ajoute les triplets déduits par R1 et R2."""
    g = Graph()
    for fichier in FICHIERS:
        g.parse(RACINE / fichier)
    if inference:
        appliquer_inference(g)
    return g
