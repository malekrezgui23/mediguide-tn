// Génère presentation/MediGuide-TN.pptx à partir de presentation/presentation.md (contenu recopié ici).
// Commande : node presentation/build.js   (après npm install dans presentation/)
const path = require("path");
const pptxgen = require("pptxgenjs");
const sharp = require("sharp");
const { applyTheme } = require("./apply_theme.js");

const PROJET = path.resolve(__dirname, "..");
const SORTIE = path.join(PROJET, "presentation", "MediGuide-TN-v2.pptx");

const THEME = {
  name: "MediGuide TN",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "17343F", lt1: "FFFFFF", dk2: "3E5763", lt2: "EDF4F5",
    accent1: "1F6F8B", accent2: "B5521B", accent3: "CFE3E8",
    accent4: "5B8E7D", accent5: "7A8691", accent6: "D5E8EC",
    hlink: "1F6F8B", folHlink: "5B8E7D",
  },
};
const H = THEME.colors;

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10 x 5.625 pouces
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  pres.title = "MédiGuide TN";
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "TITRE",
    background: { color: C.text1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.55, w: 8.8, h: 0.8,
        fontSize: 38, bold: true, color: C.background1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "CONTENU",
    background: { color: C.background1 },
    objects: [
      { rect: { x: 0, y: 0, w: 0.14, h: 5.625, fill: { color: C.accent1 }, line: { type: "none" } } },
      { placeholder: { options: { name: "title", type: "title", x: 0.45, y: 0.2, w: 9.1, h: 0.6,
        fontSize: 26, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    ],
    slideNumber: { x: 9.05, y: 5.28, w: 0.5, h: 0.25, fontSize: 10, color: C.accent5, align: "right" },
  });

  const texte = (slide, t, x, y, w, h, o = {}) =>
    slide.addText(t, { x, y, w, h, fontSize: 13, color: C.text1, margin: 0, isTextBox: true, valign: "top", ...o });
  const puces = (lignes) => lignes.map((l, i) => ({
    text: l, options: { bullet: { indent: 12 }, breakLine: i < lignes.length - 1, paraSpaceAfter: 6 } }));
  const entete = (t, taille = 11.5) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: C.text1 }, fontSize: taille } });
  const tableau = (slide, titres, lignes, o) => {
    const rangees = [titres.map((t) => entete(t))].concat(lignes.map((l) => l.map((t, j) => ({
      text: t, options: { fontSize: o.taille || 11, color: C.text1, bold: j === 0 && o.gras !== false } }))));
    slide.addTable(rangees, { valign: "middle", border: { type: "solid", pt: 0.5, color: H.accent5 },
      margin: [0.03, 0.07, 0.03, 0.07], ...o });
  };

  // ---------- 1. Titre et thématique ----------
  let s = pres.addSlide({ masterName: "TITRE" });
  s.addText("Médicaments et génériques en Tunisie", { placeholder: "title" });
  texte(s, "Graphe de connaissances : RDFS, SPARQL, inférence et API REST", 0.6, 1.35, 8.8, 0.35, { fontSize: 16, color: C.accent3 });
  texte(s, puces([
    "Thématique : relier chaque médicament à sa substance active, son laboratoire et son prix, pour trouver ses équivalents",
    "Données : la liste des AMM (6 047 médicaments, 1 044 substances, 432 laboratoires)",
    "Prix : 289 prix réels de la liste PCT de juillet 2026 ; les 5 758 autres sont estimés et marqués comme tels",
    "Complété par IA : origine des laboratoires (17 à vérifier) et stock d'une pharmacie fictive",
    "Démarche : modéliser en RDFS, interroger en SPARQL, enrichir par inférence, exposer en JSON",
    "Outils : Python, rdflib, FastAPI",
  ]), 0.6, 1.95, 8.8, 2.55, { fontSize: 14.5, color: C.background1 });
  texte(s, "IA générative utilisée pour le code et pour compléter les données.", 0.6, 4.55, 8.8, 0.3, { fontSize: 12, italic: true, color: C.accent3 });
  texte(s, "Web Sémantique | BDBI 3 - BDIA 3 | Mme Ahlem Tayachi | Projet réalisé seul", 0.6, 5.0, 8.8, 0.3, { fontSize: 12, color: C.accent3 });

  // ---------- 2. Vocabulaire ----------
  s = pres.addSlide({ masterName: "CONTENU" });
  s.addText("Vocabulaire RDFS", { placeholder: "title" });
  const schema = path.join(PROJET, "ontologie", "schema.png");
  const taille = await sharp(schema).metadata();
  const hImg = 4.1, wImg = hImg * taille.width / taille.height;
  s.addImage({ path: schema, x: 0.3, y: 0.95, w: wImg, h: hImg,
    altText: "Schéma du vocabulaire : classes, propriétés et vocabulaires réutilisés" });
  const xv = 0.3 + wImg + 0.12;
  texte(s, puces([
    "13 classes, 18 propriétés dont 3 réutilisées",
    "subClassOf : Generique sous MedicamentCopie, sous Medicament, sous schema:Drug",
    "subPropertyOf : substanceUnique et substanceAssociee sous contientSubstance",
    "domain et range sur chaque propriété",
    "Réutilisés : schema.org, FOAF, Dublin Core",
  ]), xv, 1.05, 9.7 - xv, 3.95, { fontSize: 11.5 });

  // ---------- 3. Requêtes ----------
  s = pres.addSlide({ masterName: "CONTENU" });
  s.addText("Requêtes SPARQL", { placeholder: "title" });
  tableau(s, ["Requête", "Concept", "Question posée"], [
    ["nombre_medicaments", "COUNT", "Combien de médicaments dans le guide ?"],
    ["top_substances", "COUNT + GROUP BY + ORDER BY", "Quelles substances ont le plus de médicaments ?"],
    ["medicaments", "Jointure, filtres par initBindings", "Quels médicaments pour cette substance, selon la forme, l'origine et le type, du moins cher au plus cher ?"],
    ["sous_classes_sans_laboratoire_tunisien", "FILTER NOT EXISTS + sous-requête", "Quels types de médicaments n'ont aucun laboratoire tunisien ?"],
    ["substances_vitales_source_unique", "HAVING + GROUP_CONCAT", "Quelles substances d'un médicament vital n'ont qu'un seul laboratoire ?"],
    ["equivalents_medicament", "Jointure sur le graphe + OPTIONAL", "Quels sont les équivalents de ce médicament, et sont-ils en stock ?"],
  ], { x: 0.45, y: 0.95, w: 9.1, colW: [3.05, 2.45, 3.6], rowH: 0.5 });
  texte(s, "Exemples : paracétamol, 169 médicaments ; 8 types de médicaments sans laboratoire tunisien ; 71 substances à laboratoire unique ; Doliprane 500 mg comprimé, 13 équivalents.",
    0.45, 4.6, 9.1, 0.55, { fontSize: 12.5, italic: true, color: C.text2 });

  // ---------- 4. Inférence ----------
  s = pres.addSlide({ masterName: "CONTENU" });
  s.addText("Inférence RDFS : 24 293 triplets déduits", { placeholder: "title" });
  tableau(s, ["Règle du cours", "Écrit pour Doliprane 500 mg", "Déduit"], [
    ["R1, sous-classes (17 143 triplets)", "a med:Princeps", "a med:Medicament, a schema:Drug"],
    ["R2, sous-propriétés (7 150 triplets)", "substanceUnique paracétamol", "contientSubstance paracétamol"],
  ], { x: 0.45, y: 0.92, w: 9.1, colW: [3.1, 2.9, 3.1], rowH: 0.42 });
  tableau(s, ["Même question", "Sans", "Avec", "Règle"], [
    ["Triplets du graphe", "96 078", "120 371", "R1 + R2"],
    ["Nombre de médicaments", "0", "6 047", "R1"],
    ["Copies (génériques et biosimilaires)", "0", "4 184", "R1"],
    ["Équivalents de Doliprane 500 mg", "0", "13", "R1"],
    ["Médicaments au paracétamol", "0", "169", "R2"],
  ], { x: 0.45, y: 2.32, w: 5.5, colW: [3.05, 0.85, 0.85, 0.75], rowH: 0.36, gras: false });
  texte(s, "Ce que ça change", 6.2, 2.3, 3.35, 0.3, { fontSize: 14, bold: true, color: C.accent1 });
  texte(s, puces([
    "Dans les données, on écrit seulement le type et la propriété les plus précis.",
    "Sans inférence, une recherche sur le paracétamol ne donne rien : le terme général n'est jamais écrit.",
    "Avec R2, elle réunit les 87 médicaments au paracétamol seul et les 82 en association.",
    "Les triplets déduits sont dans resultats/triplets_inferes.ttl.",
  ]), 6.2, 2.62, 3.35, 2.55, { fontSize: 11.5 });

  // ---------- 5. Web service ----------
  s = pres.addSlide({ masterName: "CONTENU" });
  s.addText("Web service REST (FastAPI)", { placeholder: "title" });
  tableau(s, ["Endpoint (GET)", "Qui s'en sert, pour quoi"], [
    ["/medicaments", "Patient, pharmacien : chercher par substance, forme, origine, type"],
    ["/medicaments/{amm}/equivalents", "Pharmacien : remplacer un produit, voir le stock et l'économie"],
    ["/substances/top", "Voir où le choix est le plus large"],
    ["/substances/source-unique", "Ministère : risque de rupture"],
    ["/sous-classes/dependance-etranger", "Ministère : dépendance à l'étranger"],
    ["/statistiques/inference", "Voir ce que l'inférence ajoute"],
  ], { x: 0.45, y: 0.92, w: 5.3, colW: [2.5, 2.8], rowH: 0.43, taille: 10.5, gras: false });
  texte(s, puces([
    "Paramètre inference=true|false sur tous les endpoints",
    "Erreurs : 404 si l'identifiant est inconnu, 422 si un paramètre est invalide",
    "Paramètres liés par initBindings, pas d'injection SPARQL",
  ]), 0.45, 4.05, 5.3, 1.15, { fontSize: 11.5 });
  texte(s, "Exemple : Micardis 40 mg, 56,838 DT", 6.0, 0.92, 3.55, 0.3, { fontSize: 13, bold: true, color: C.accent1 });
  texte(s, "GET /medicaments/1153031/equivalents", 6.0, 1.22, 3.55, 0.25, { fontSize: 10, fontFace: "Consolas", color: C.text2 });
  s.addText([
    '{ "inference": true,', '  "nombre": 2,', '  "resultats": [ {', '    "nom": "TELMISARTAN MYLAN",', '    "presentation": "B/30",',
    '    "prix": 16.255,', '    "originePrix": "reel",', '    "economiePct": 73,', '    "enStock": false', '  }, ... ] }',
  ].map((l, i, t) => ({ text: l, options: { breakLine: i < t.length - 1 } })), { x: 6.0, y: 1.5, w: 3.55, h: 2.15,
    fontFace: "Consolas", fontSize: 10.5, color: C.text1, fill: { color: C.background2 }, valign: "middle", margin: 6 });
  texte(s, "(réponse raccourcie) 73 % moins cher par comprimé : les deux prix sont réels.", 6.0, 3.7, 3.55, 0.45, { fontSize: 11, italic: true, color: C.text2 });
  texte(s, [{ text: "Limite : ", options: { bold: true, color: C.accent2 } },
            { text: "aucun prix réel ne concerne un laboratoire tunisien. Pour eux, l'économie affichée est une illustration." }],
    6.0, 4.2, 3.55, 0.9, { fontSize: 11.5 });

  await pres.writeFile({ fileName: SORTIE });
  await applyTheme(SORTIE, THEME);
  console.log("écrit :", SORTIE);
}

main().catch((e) => { console.error(e); process.exit(1); });
