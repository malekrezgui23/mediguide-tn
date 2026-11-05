"""Vérifie le vocabulaire : il se charge, et il respecte les exigences du sujet.

Commande : python scripts/verifier_vocabulaire.py
"""

import sys
from pathlib import Path

from rdflib import Graph
from rdflib.namespace import RDF, RDFS

RACINE = Path(__file__).resolve().parent.parent


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    g = Graph().parse(RACINE / "ontologie" / "vocabulaire.ttl")
    classes = set(g.subjects(RDF.type, RDFS.Class))
    proprietes = set(g.subjects(RDF.type, RDF.Property))
    sans_domaine = [p for p in proprietes if (p, RDFS.domain, None) not in g]
    sans_portee = [p for p in proprietes if (p, RDFS.range, None) not in g]
    print(f"{len(classes)} classes, {len(proprietes)} propriétés")
    print(f"{len(list(g.triples((None, RDFS.subClassOf, None))))} rdfs:subClassOf, "
          f"{len(list(g.triples((None, RDFS.subPropertyOf, None))))} rdfs:subPropertyOf")
    print(f"Sans domaine : {sans_domaine} ; sans portée : {sans_portee}")
    assert len(classes) >= 5 and len(proprietes) >= 8 and not sans_domaine and not sans_portee


if __name__ == "__main__":
    main()
