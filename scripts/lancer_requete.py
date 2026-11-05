"""Lance une requête SPARQL du dossier requetes/ et affiche le résultat (pour tester vite).

Commandes :
  python scripts/lancer_requete.py requetes/q0_nombre_medicaments.rq
  python scripts/lancer_requete.py requetes/q0_nombre_medicaments.rq --inference
  python scripts/lancer_requete.py requetes/q2_medicaments_par_substance_forme_origine_type.rq --inference --param substance=medd:substance-paracetamol
"""

import argparse
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
from inference.inferer import appliquer_inference  # noqa: E402

PREFIXES = {"med:": Namespace("http://mediguide-tn.org/vocab#"),
            "medd:": Namespace("http://mediguide-tn.org/donnees/")}


def charger(inference: bool) -> Graph:
    g = Graph()
    for fichier in ("ontologie/vocabulaire.ttl", "donnees/medicaments.ttl", "donnees/pharmacies.ttl"):
        g.parse(RACINE / fichier)
    if inference:
        appliquer_inference(g)
    return g


def valeur(texte: str):
    """« medd:substance-paracetamol » -> URI ; tout le reste -> littéral (texte)."""
    for prefixe, ns in PREFIXES.items():
        if texte.startswith(prefixe):
            return ns[texte[len(prefixe):]]
    return Literal(texte)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Lance une requête .rq sur le graphe.")
    parser.add_argument("requete", help="fichier .rq")
    parser.add_argument("--inference", action="store_true", help="appliquer R1 et R2 avant la requête")
    parser.add_argument("--param", action="append", default=[], help="nom=valeur, lié par initBindings")
    args = parser.parse_args()

    parametres = {nom: valeur(v) for nom, v in (p.split("=", 1) for p in args.param)}
    resultats = charger(args.inference).query(Path(args.requete).read_text(encoding="utf-8"),
                                              initBindings=parametres)
    print(f"{'Avec' if args.inference else 'Sans'} inférence · {args.requete} · paramètres : {args.param or 'aucun'}")
    print(" | ".join(str(v) for v in resultats.vars))
    lignes = 0
    for ligne in resultats:
        print(" | ".join("" if v is None else str(v).replace("http://mediguide-tn.org/donnees/", "medd:") for v in ligne))
        lignes += 1
    print(f"({lignes} ligne(s))")


if __name__ == "__main__":
    main()
