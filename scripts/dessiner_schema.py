"""Dessine ontologie/schema.png à partir de ontologie/vocabulaire.ttl, et vérifie que tout y apparaît.

Commande : python scripts/dessiner_schema.py   (dépendance : matplotlib)
Sur le schéma : flèche pleine = propriété (domaine -> portée) ; flèche pointillée = rdfs:subClassOf ;
bleu = nos classes ; gris = vocabulaires réutilisés.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from rdflib import Graph  # noqa: E402
from rdflib.namespace import RDF, RDFS  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent
MED = "http://mediguide-tn.org/vocab#"

POSITIONS = {
    "schema:Drug": (4.8, 9.4), "Medicament": (4.8, 8.0), "Princeps": (1.2, 6.6), "MedicamentCopie": (4.1, 6.6),
    "Generique": (2.4, 5.2), "Biosimilaire": (5.3, 5.2),
    "schema:Pharmacy": (14.5, 9.4), "Pharmacie": (10.5, 9.4),
    "foaf:Organization": (15.9, 8.0), "Laboratoire": (13.0, 8.0), "LaboratoireTunisien": (11.8, 6.7),
    "LaboratoireEtranger": (15.4, 6.7),
    "SubstanceActive": (12.5, 4.7), "Forme": (8.6, 3.6), "SousClasseTherapeutique": (11.3, 2.2),
    "ClasseTherapeutique": (15.4, 2.2),
}
LIENS = {  # propriété -> courbure de la flèche, position du libellé le long de la flèche
    "substanceUnique": -0.16, "substanceAssociee": 0.0, "contientSubstance": 0.16,
}
LITTERAUX = ["dosage", "dosageNormalise", "codeComposition", "presentation", "niveauVEIC", "prixPublic", "originePrix",
             "foaf:name", "dcterms:date", "schema:identifier"]
BLEU, GRIS, ACCENT, TEXTE = "#1F6F8B", "#7A8691", "#C2571A", "#1E2A32"


def court(uri) -> str:
    texte = str(uri)
    if texte.startswith(MED):
        return texte[len(MED):]
    return {"https://schema.org/": "schema:", "http://xmlns.com/foaf/0.1/": "foaf:"}[texte.rsplit("/", 1)[0] + "/"] + texte.rsplit("/", 1)[1]


def boite(ax, nom: str):
    x, y = POSITIONS[nom]
    externe = ":" in nom
    largeur = 0.14 * len(nom) + 0.5
    ax.add_patch(FancyBboxPatch((x - largeur / 2, y - 0.27), largeur, 0.54, boxstyle="round,pad=0.03,rounding_size=0.12",
                                facecolor="#FFFFFF" if externe else BLEU, edgecolor=GRIS if externe else BLEU,
                                linewidth=1.4, linestyle="--" if externe else "-", zorder=3))
    ax.text(x, y, nom, ha="center", va="center", fontsize=10, color=GRIS if externe else "white",
            fontweight="bold", zorder=4)


def fleche(ax, depart, arrivee, couleur, style="-", courbure=0.0, epaisseur=1.3):
    ax.add_patch(FancyArrowPatch(POSITIONS[depart], POSITIONS[arrivee], arrowstyle="-|>", mutation_scale=13, color=couleur,
                                 linestyle=style, linewidth=epaisseur, connectionstyle=f"arc3,rad={courbure}",
                                 shrinkA=14, shrinkB=14, zorder=2))


def main():
    g = Graph().parse(RACINE / "ontologie" / "vocabulaire.ttl")
    fig, ax = plt.subplots(figsize=(16, 9.2))
    ax.set_xlim(-0.6, 17.8)
    ax.set_ylim(0.6, 10.3)
    ax.axis("off")

    dessinees = set()
    for sous, sur in g.subject_objects(RDFS.subClassOf):
        fleche(ax, court(sous), court(sur), GRIS, style=":", epaisseur=1.6)
    for nom in POSITIONS:
        boite(ax, nom)

    libelles = {
        "substanceUnique": (8.3, 7.15), "substanceAssociee": (8.15, 6.3), "contientSubstance": (9.2, 4.95),
        "fabriquePar": (8.8, 8.22), "aPourForme": (7.15, 4.45), "aPourSousClasse": (10.9, 3.05),
        "sousClasseDe": (13.6, 2.72), "aEnStock": (7.6, 9.0),
    }
    for p in g.subjects(RDF.type, RDF.Property):
        nom = court(p)
        domaine, portee = court(g.value(p, RDFS.domain)), g.value(p, RDFS.range)
        if str(portee).startswith("http://www.w3.org/2001/XMLSchema#"):
            dessinees.add(nom)
            continue
        fleche(ax, domaine, court(portee), ACCENT if g.value(p, RDFS.subPropertyOf) is None and nom in LIENS else BLEU,
               courbure=LIENS.get(nom, 0.0))
        x, y = libelles[nom]
        ax.text(x, y, nom, fontsize=9.5, color=ACCENT if nom == "contientSubstance" else BLEU, ha="center", va="center",
                fontstyle="italic", bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.2}, zorder=5)
        dessinees.add(nom)
    for sous, sur in g.subject_objects(RDFS.subPropertyOf):
        dessinees.add(court(sous))

    ax.text(0.0, 3.25, "Propriétés à valeur simple de Medicament :", fontsize=10, fontweight="bold", color=TEXTE)
    ax.text(0.0, 2.85, "dosage, dosageNormalise, codeComposition,", fontsize=10, color=BLEU)
    ax.text(0.0, 2.45, "presentation, niveauVEIC, prixPublic, originePrix", fontsize=10, color=BLEU)
    ax.text(0.0, 2.0, "Réutilisées : foaf:name, dcterms:date, schema:identifier", fontsize=10, color=GRIS)
    ax.text(0.0, 0.9, "⋯⋯▶ rdfs:subClassOf      ——▶ propriété (domaine → portée)      "
                        "substanceUnique et substanceAssociee : rdfs:subPropertyOf contientSubstance (en orange)",
            fontsize=9.5, color=TEXTE)
    ax.text(-0.3, 10.0, "Vocabulaire de MédiGuide TN", fontsize=15, fontweight="bold", color=TEXTE)

    classes = {court(c) for c in g.subjects(RDF.type, RDFS.Class)}
    proprietes = {court(p) for p in g.subjects(RDF.type, RDF.Property)}
    assert classes <= set(POSITIONS), f"Classes absentes du schéma : {classes - set(POSITIONS)}"
    assert proprietes <= dessinees, f"Propriétés absentes du schéma : {proprietes - dessinees}"
    fig.savefig(RACINE / "ontologie" / "schema.png", dpi=150, bbox_inches="tight", facecolor="white")
    print(f"ontologie/schema.png : {len(classes)} classes, {len(proprietes)} propriétés")


if __name__ == "__main__":
    main()
