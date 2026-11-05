"""Conversion du CSV complété en triplets RDF (contrat 1 de PLAN.md).

Commande : python scripts/csv_vers_rdf.py
Entrées  : donnees/brut/liste_amm_complete.csv, donnees/laboratoires.csv
Sorties  : donnees/medicaments.ttl, donnees/pharmacies.ttl (pharmacie fictive)
"""

import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

from rdflib import Graph, Literal, Namespace
from rdflib.namespace import DCTERMS, FOAF, RDF, XSD

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "scripts"))
from outils import code_composition, normaliser_dosage, slug, substances  # noqa: E402

MED = Namespace("http://mediguide-tn.org/vocab#")
MEDD = Namespace("http://mediguide-tn.org/donnees/")
SCHEMA = Namespace("https://schema.org/")

TYPES = {"Générique": MED.Generique, "Princeps": MED.Princeps, "Biosimilaire": MED.Biosimilaire}
IMPLANTATIONS = {"tunisie": MED.LaboratoireTunisien, "etranger": MED.LaboratoireEtranger}
PHARMACIE = "demo"
PART_EN_STOCK = 30  # % des médicaments en stock dans la pharmacie fictive
HORS_STOCK = {"doliprane"}  # le scénario du sujet : le pharmacien n'a plus de Doliprane


def creer_graphe() -> Graph:
    g = Graph()
    for prefixe, ns in (("med", MED), ("medd", MEDD), ("schema", SCHEMA), ("dcterms", DCTERMS), ("foaf", FOAF), ("xsd", XSD)):
        g.bind(prefixe, ns)
    return g


def lire_medicaments() -> list[dict]:
    with open(RACINE / "donnees" / "brut" / "liste_amm_complete.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def detecter_type(ligne: dict):
    """La classe la plus précise (règle 1 du contrat 1) : jamais med:Medicament."""
    return TYPES[ligne["G/P/B"].strip()]


def nommer(g: Graph, entite, nom: str):
    """Un seul nom par entité : « VALSARTAN » et « valsartan » ont le même slug, on garde le premier rencontré."""
    if (entite, FOAF.name, None) not in g:
        g.add((entite, FOAF.name, Literal(nom)))


def medicament_vers_triplets(g: Graph, ligne: dict):
    amm = ligne["AMM"].strip()
    med = MEDD[f"medicament-{slug(amm)}"]
    g.add((med, RDF.type, detecter_type(ligne)))
    g.add((med, FOAF.name, Literal(ligne["Nom"].strip())))
    g.add((med, SCHEMA.identifier, Literal(amm)))
    date = datetime.strptime(ligne["Date AMM"].strip(), "%m/%d/%Y").date().isoformat()
    g.add((med, DCTERMS.date, Literal(date, datatype=XSD.date)))
    g.add((med, MED.prixPublic, Literal(ligne["prix_public"], datatype=XSD.decimal)))
    g.add((med, MED.originePrix, Literal(ligne["origine_prix"])))

    for colonne, propriete in (("Présentation", MED.presentation), ("VEIC", MED.niveauVEIC), ("Dosage", MED.dosage)):
        if ligne[colonne].strip():
            g.add((med, propriete, Literal(ligne[colonne].strip())))
    if ligne["Dosage"].strip():
        g.add((med, MED.dosageNormalise, Literal(normaliser_dosage(ligne["Dosage"]))))

    # règle 3 : seulement substanceUnique / substanceAssociee, jamais contientSubstance
    noms = substances(ligne["DCI"])
    if noms:
        g.add((med, MED.codeComposition, Literal(code_composition(ligne["DCI"]))))
    propriete = MED.substanceUnique if len(noms) == 1 else MED.substanceAssociee
    for nom in noms:
        substance = MEDD[f"substance-{slug(nom)}"]
        g.add((med, propriete, substance))
        g.add((substance, RDF.type, MED.SubstanceActive))
        nommer(g, substance, nom)

    forme = MEDD[f"forme-{slug(ligne['Forme'])}"]
    g.add((med, MED.aPourForme, forme))
    g.add((forme, RDF.type, MED.Forme))
    nommer(g, forme, ligne["Forme"].strip())

    # Le laboratoire est typé plus bas, depuis donnees/laboratoires.csv (règle 2)
    g.add((med, MED.fabriquePar, MEDD[f"laboratoire-{slug(ligne['Laboratoire'])}"]))

    sous_classe = MEDD[f"sousclasse-{slug(ligne['Sous Classe'])}"]
    classe = MEDD[f"classe-{slug(ligne['Classe'])}"]
    g.add((med, MED.aPourSousClasse, sous_classe))
    g.add((sous_classe, RDF.type, MED.SousClasseTherapeutique))
    nommer(g, sous_classe, ligne["Sous Classe"].strip())
    g.add((sous_classe, MED.sousClasseDe, classe))
    g.add((classe, RDF.type, MED.ClasseTherapeutique))
    nommer(g, classe, ligne["Classe"].strip())


def laboratoires_vers_triplets(g: Graph):
    with open(RACINE / "donnees" / "laboratoires.csv", encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f):
            laboratoire = MEDD[f"laboratoire-{l['slug']}"]
            g.add((laboratoire, RDF.type, IMPLANTATIONS[l["implantation"]]))
            g.add((laboratoire, FOAF.name, Literal(l["nom"].strip())))


def ecrire_pharmacie(lignes: list[dict]) -> int:
    """Pharmacie fictive : environ 30 % des médicaments en stock, choix stable d'un lancement à l'autre."""
    g = creer_graphe()
    pharmacie = MEDD[f"pharmacie-{PHARMACIE}"]
    g.add((pharmacie, RDF.type, MED.Pharmacie))
    g.add((pharmacie, FOAF.name, Literal("Pharmacie de démonstration (fictive)")))
    en_stock = 0
    for amm, nom in {l["AMM"].strip(): slug(l["Nom"]) for l in lignes}.items():
        tirage = int(hashlib.sha256(amm.encode()).hexdigest()[8:16], 16) % 100
        if tirage < PART_EN_STOCK and nom not in HORS_STOCK:
            g.add((pharmacie, MED.aEnStock, MEDD[f"medicament-{slug(amm)}"]))
            en_stock += 1
    g.serialize(RACINE / "donnees" / "pharmacies.ttl", format="turtle")
    return en_stock


def main():
    g = creer_graphe()
    lignes = lire_medicaments()
    for ligne in lignes:
        medicament_vers_triplets(g, ligne)
    laboratoires_vers_triplets(g)
    g.serialize(RACINE / "donnees" / "medicaments.ttl", format="turtle")

    nb_amm = len({l["AMM"].strip() for l in lignes})
    nb_instances = len(set(g.subjects(MED.fabriquePar, None)))
    assert nb_instances == nb_amm, f"{nb_instances} médicaments dans le graphe pour {nb_amm} AMM du CSV"
    for generale in (MED.Medicament, MED.MedicamentCopie, MED.Laboratoire):
        assert not list(g.subjects(RDF.type, generale)), f"Classe générale écrite dans les données : {generale}"
    assert not list(g.triples((None, MED.contientSubstance, None))), "Propriété générale écrite dans les données"
    sans_prix = set(g.subjects(MED.fabriquePar, None)) - set(g.subjects(MED.prixPublic, None))
    assert not sans_prix, f"{len(sans_prix)} médicaments sans prix"

    en_stock = ecrire_pharmacie(lignes)
    print(f"{len(lignes)} lignes CSV -> {nb_instances} médicaments, {len(g)} triplets dans donnees/medicaments.ttl")
    print(f"Pharmacie fictive : {en_stock} médicaments en stock dans donnees/pharmacies.ttl")


if __name__ == "__main__":
    main()
