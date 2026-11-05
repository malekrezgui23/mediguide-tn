# Script de démo (5 min)

Avant : un terminal à la racine du projet, puis attendre environ 15 secondes (chargement du graphe).

`.venv\Scripts\python -m uvicorn app.main:app`

| # | Action | Ce qu'on dit | Résultat attendu |
|---|---|---|---|
| 1 | Ouvrir http://127.0.0.1:8000/docs | « Le web service : 6 endpoints, documentés automatiquement par FastAPI. » | la liste des endpoints |
| 2 | `/statistiques/inference` avec `inference=false` puis `true` | « Sans inférence, aucun médicament n'est un med:Medicament ; R1 et R2 déduisent 24 293 triplets. » | 0 → 6 047 médicaments ; 96 078 → 120 371 triplets |
| 3 | `/substances/top` → `limite=5` | « Q1 : les substances où le choix est le plus large. » | Paracétamol 169, Amlodipine 151, Hydrochlorothiazide 136, Amoxicilline 128, Valsartan 100 |
| 4 | `/medicaments` → `substance=paracetamol`, `origine=tunisien`, `type=copie` | « Q2 : `copie` n'existe pas dans les données, R1 le déduit. Résultats du moins cher au plus cher. » | 120 résultats, limités à 50 par défaut |
| 5 | `/medicaments/{amm}/equivalents` → `amm=9103482`, `en_stock=true` | « Q5 : le pharmacien n'a plus de Doliprane. La pharmacie est fictive. » | Analgan B/20, SIPHAT, 2,500 DT, 41 % par comprimé, prix estimé |
| 6 | `/medicaments/{amm}/equivalents` → `amm=1153031`, `en_stock=false` | « Q5 sur des prix réels des deux côtés : Micardis 40 mg. » | Telmisartan Mylan B/30, 16,255 DT, 73 % par comprimé, `originePrix: reel` |
| 7 | `/sous-classes/dependance-etranger` | « Q3 : l'analyste du ministère. » | 8 sous-classes, en tête les antihémorragiques (69 médicaments) |
| 8 | `/substances/source-unique` | « Q4 : le risque de rupture. » | 71 substances |
| 9 | `/medicaments/{amm}/equivalents` → `amm=000` ; puis dans la barre d'adresse : http://127.0.0.1:8000/substances/top?limite=0 | « Gestion des erreurs. » | 404 « Médicament inconnu : AMM 000 » ; 422 |
