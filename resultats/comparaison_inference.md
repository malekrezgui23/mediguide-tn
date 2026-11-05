# Comparaison sans / avec inférence

Généré par `python scripts/comparer_inference.py` (ne pas modifier à la main).

- Graphe sans inférence : 96078 triplets (vocabulaire + médicaments + pharmacie).
- Graphe avec inférence : 120371 triplets, soit **24293 triplets inférés** (17143 `rdf:type` par R1, 7150 `med:contientSubstance` par R2).
- Les triplets inférés sont dans `resultats/triplets_inferes.ttl`.

| Requête | Sans inférence | Avec inférence | Règle |
|---|---|---|---|
| Q0 · Nombre de médicaments (`?m a med:Medicament`) | 0 | 6047 | R1 |
| Copies d'un médicament d'origine (`?m a med:MedicamentCopie`) | 0 | 4184 | R1 |
| Q2 · Médicaments qui contiennent du paracétamol (`med:contientSubstance`) | 0 | 169 | R2 |
| Q1 · Top 5 des substances | aucun résultat | PARACETAMOL (169), AMLODIPINE (151), HYDROCHLOROTHIAZIDE (136), AMOXICILLINE (128), VALSARTAN (100) | R2 |

## Commentaires

- **Q0 · Nombre de médicaments** : Les médicaments ne sont écrits que `med:Generique`, `med:Biosimilaire` ou `med:Princeps` (règle d'écriture 1). R1 en boucle remonte la hiérarchie jusqu'à `med:Medicament`.
- **Copies d'un médicament d'origine** : Une seule question pour les génériques et les biosimilaires, sans avoir à citer les deux types.
- **Q2 · Médicaments qui contiennent du paracétamol** : Les données n'utilisent que `med:substanceUnique` et `med:substanceAssociee` (règle d'écriture 3). R2 en déduit `med:contientSubstance` : les 87 médicaments au paracétamol seul, plus ceux où il est associé à une autre substance. Sans cette règle, un pharmacien manquerait ces derniers.
- **Q1 · Top 5 des substances** : Même cause que Q2 : sans inférence, aucun médicament ne « contient » de substance. Avec R2, le classement compte les substances seules et en association.
