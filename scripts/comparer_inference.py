"""Compare les mêmes requêtes sans et avec inférence (étape 3 du sujet).

Commande : python scripts/comparer_inference.py
Sorties  : resultats/comparaison_inference.md (tableau commenté)
           resultats/triplets_inferes.ttl (seulement les triplets ajoutés par R1 et R2)
"""

import sys
from pathlib import Path

from rdflib import Graph, Namespace
from rdflib.namespace import RDF

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
from inference.inferer import appliquer_inference  # noqa: E402

MED = Namespace("http://mediguide-tn.org/vocab#")
MEDD = Namespace("http://mediguide-tn.org/donnees/")
SCHEMA = Namespace("https://schema.org/")
PREFIXES = """PREFIX med: <http://mediguide-tn.org/vocab#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
"""

Q0 = PREFIXES + "SELECT (COUNT(DISTINCT ?m) AS ?n) WHERE { ?m a med:Medicament }"
COPIES = PREFIXES + "SELECT (COUNT(DISTINCT ?m) AS ?n) WHERE { ?m a med:MedicamentCopie }"
SUBSTANCE = PREFIXES + "SELECT (COUNT(DISTINCT ?m) AS ?n) WHERE { ?m med:contientSubstance ?substance }"
Q1 = PREFIXES + """SELECT ?nom (COUNT(DISTINCT ?m) AS ?n)
WHERE { ?m med:contientSubstance ?s . ?s foaf:name ?nom }
GROUP BY ?nom ORDER BY DESC(?n) ?nom LIMIT 5"""


def charger() -> Graph:
    g = Graph()
    for fichier in ("ontologie/vocabulaire.ttl", "donnees/medicaments.ttl", "donnees/pharmacies.ttl"):
        g.parse(RACINE / fichier)
    return g


def nombre(g: Graph, requete: str, **parametres) -> int:
    return int(next(iter(g.query(requete, initBindings=parametres)))[0])


def top(g: Graph) -> str:
    lignes = [f"{nom} ({n})" for nom, n in g.query(Q1)]
    return ", ".join(lignes) if lignes else "aucun résultat"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sans = charger()
    avec = charger()
    ajoutes = appliquer_inference(avec)

    # vérification : un générique devient aussi MedicamentCopie, Medicament et schema:Drug (R1 en boucle)
    generique = next(sans.subjects(RDF.type, MED.Generique))
    for classe in (MED.MedicamentCopie, MED.Medicament, SCHEMA.Drug):
        assert (generique, RDF.type, classe) in avec, f"{generique} n'est pas {classe}"

    inferes = avec - sans
    inferes.namespace_manager = sans.namespace_manager
    (RACINE / "resultats").mkdir(exist_ok=True)
    inferes.serialize(RACINE / "resultats" / "triplets_inferes.ttl", format="turtle")

    par_type = len(list(inferes.triples((None, RDF.type, None))))
    par_substance = len(list(inferes.triples((None, MED.contientSubstance, None))))
    paracetamol = MEDD["substance-paracetamol"]
    seul_sans = len(set(sans.subjects(MED.substanceUnique, paracetamol)))
    lignes = [
        ("Q0 · Nombre de médicaments (`?m a med:Medicament`)", nombre(sans, Q0), nombre(avec, Q0), "R1",
         "Les médicaments ne sont écrits que `med:Generique`, `med:Biosimilaire` ou `med:Princeps` (règle d'écriture 1). "
         "R1 en boucle remonte la hiérarchie jusqu'à `med:Medicament`."),
        ("Copies d'un médicament d'origine (`?m a med:MedicamentCopie`)", nombre(sans, COPIES), nombre(avec, COPIES), "R1",
         "Une seule question pour les génériques et les biosimilaires, sans avoir à citer les deux types."),
        ("Q2 · Médicaments qui contiennent du paracétamol (`med:contientSubstance`)",
         nombre(sans, SUBSTANCE, substance=paracetamol), nombre(avec, SUBSTANCE, substance=paracetamol), "R2",
         f"Les données n'utilisent que `med:substanceUnique` et `med:substanceAssociee` (règle d'écriture 3). "
         f"R2 en déduit `med:contientSubstance` : les {seul_sans} médicaments au paracétamol seul, plus ceux où il est "
         f"associé à une autre substance. Sans cette règle, un pharmacien manquerait ces derniers."),
        ("Q1 · Top 5 des substances", top(sans), top(avec), "R2",
         "Même cause que Q2 : sans inférence, aucun médicament ne « contient » de substance. "
         "Avec R2, le classement compte les substances seules et en association."),
    ]

    md = ["# Comparaison sans / avec inférence", "",
          "Généré par `python scripts/comparer_inference.py` (ne pas modifier à la main).", "",
          f"- Graphe sans inférence : {len(sans)} triplets (vocabulaire + médicaments + pharmacie).",
          f"- Graphe avec inférence : {len(avec)} triplets, soit **{ajoutes} triplets inférés** "
          f"({par_type} `rdf:type` par R1, {par_substance} `med:contientSubstance` par R2).",
          "- Les triplets inférés sont dans `resultats/triplets_inferes.ttl`.", "",
          "| Requête | Sans inférence | Avec inférence | Règle |", "|---|---|---|---|"]
    md += [f"| {q} | {s} | {a} | {r} |" for q, s, a, r, _ in lignes]
    md += ["", "## Commentaires", ""] + [f"- **{q.split(' (')[0]}** : {c}" for q, _, _, _, c in lignes]
    (RACINE / "resultats" / "comparaison_inference.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"{len(sans)} triplets sans inférence, {len(avec)} avec : {ajoutes} triplets inférés "
          f"({par_type} rdf:type, {par_substance} med:contientSubstance)")
    for q, s, a, r, _ in lignes:
        print(f"{q.split(' (')[0]} : sans = {s} | avec = {a} ({r})")
    print("-> resultats/comparaison_inference.md, resultats/triplets_inferes.ttl")


if __name__ == "__main__":
    main()
