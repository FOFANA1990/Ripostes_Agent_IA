# CNC — Veille & Riposte face à une polémique virale

Projet de bout en bout traitant une polémique sur X/Twitter impliquant le CNC : depuis l'analyse descriptive du corpus jusqu'à une chaîne d'agents IA de détection, d'analyse et de proposition de riposte, supervisée par un humain via un tableau de bord de validation.

Le projet est organisé en trois phases qui s'enchaînent :

```
Phase 1                    Phase 2                          Phase 3
Analyse descriptive   -->  Chaîne d'agents IA          -->  Monitoring & validation
(comprendre la crise)      (détection, analyse, riposte)    (interface humaine de décision)
```

## Vue d'ensemble

| Question | Réponse apportée par le projet |
|---|---|
| Qui a lancé ou amplifié la polémique ? | Phase 1 : reconstruction des cascades de retweets, identification des primo-diffuseurs et amplificateurs. |
| Comment, pourquoi, depuis quand, à quelle vitesse ? | Phase 1 : indicateurs de diffusion, angles narratifs, chronologie et vitesse de propagation. |
| Comment détecter automatiquement un emballement similaire ? | Phase 2 : agent de détection déterministe, calibré sur les seuils mesurés en phase 1. |
| Comment qualifier l'événement sans hallucination ? | Phase 2 : agent d'analyse (LLM ancré sur des faits, sortie typée). |
| Comment préparer une réponse ? | Phase 2 : agent de riposte (LLM, brouillon jamais publié automatiquement). |
| Qui valide avant publication ? | Phase 3 : tableau de bord où un opérateur CNC valide, édite, rejette ou demande un fact-check. |

## Structure du dépôt

```
cnc-veille-riposte/
├── data.xlsx                            Corpus brut : 35 396 posts X/Twitter (non versionné, voir plus bas)
├── dictionnaire_bdd.xlsx                Dictionnaire des données : nom et explication de chaque colonne du corpus
├── analyse_corpus.py                    Phase 1 : script d'analyse descriptive du corpus
├── analyse_corpus.ipynb                 Phase 1 : même analyse, version notebook pédagogique
├── requirements.txt                     Dépendances de la phase 1 (analyse descriptive)
│
├── agents_cnc/                         Phase 2 : chaîne d'agents IA
│   ├── README.md                       Documentation détaillée de ce module
│   ├── config.py / config.yaml         Configuration (générique + domaine), validée par Pydantic
│   ├── data_loader.py                  Chargement et nettoyage du corpus, mots-clés narratifs
│   ├── schemas.py                      Contrats de données (Pydantic) échangés entre agents
│   ├── agents/                         Agent 1 (détection), agent 2 (analyse), agent 3 (riposte)
│   ├── orchestrator.py                 Enchaînement séquentiel des 3 agents (mode batch)
│   ├── streaming.py / triggers.py      Rejeu heure par heure et politique de déclenchement
│   ├── run_demo.py                     Point d'entrée CLI : traitement batch du corpus
│   └── run_stream.py                   Point d'entrée CLI : rejeu en temps réel simulé
│
├── monitoring/                         Phase 3 : interface de supervision humaine
│   ├── README.md                       Documentation détaillée de ce module
│   ├── backend/                        API FastAPI (dashboard, événements, décisions, audit)
│   └── frontend/                       Dashboard React + TypeScript + Tailwind
│
├── Analyse_polemique_CNC.pptx          Support de présentation des résultats de la phase 1
├── Agents_IA_CNC_methodologie.pptx     Dossier technique : méthodologie et architecture des agents
└── Phase2_Agents_IA_CNC.pptx           Feuille de route de la phase 2
```

Chaque module (`agents_cnc/`, `monitoring/`) dispose de son propre README détaillé : installation, commandes, structure interne. Ce document racine donne la vue d'ensemble et explique comment les trois phases s'articulent.

## Phase 1 — Analyse descriptive du corpus

But : comprendre, à partir des seules données du corpus (~35 000 posts, 42 jours), comment la polémique est née et s'est propagée, sans hypothèse a priori. Cinq questions guident l'analyse : qui a lancé ou amplifié, comment, pourquoi ça a pris, depuis quand, à quelle vitesse.

Fichiers : `analyse_corpus.py` (script CLI) et `analyse_corpus.ipynb` (même analyse, présentée section par section avec visualisations).

Installation et dépendances (`pandas`, `numpy`, `openpyxl`, `matplotlib`, `jupyter`) :

```bash
pip install -r requirements.txt
```

Indicateurs produits : chiffres clés (volume, auteurs, reach, période), répartition de l'engagement et du sentiment, primo-diffuseurs et amplificateurs (cascades de retweets reconstruites), timeline journalière, vitesse de propagation (pic horaire, délai jusqu'au pic, temps de doublement), hashtags les plus fréquents, et poids de chaque angle narratif (argent public, anti-France, filiation des personnalités citées, clivage politique, censure/liberté de création).

Ces indicateurs — en particulier le temps de doublement (~49 heures) et le volume du pic (751 posts/heure) — servent ensuite de référence pour calibrer les seuils d'alerte de la phase 2.

## Phase 2 — Chaîne d'agents IA (`agents_cnc/`)

But : transformer les enseignements de la phase 1 en un système capable de détecter un emballement similaire et de préparer une réponse, sans halluciner.

Architecture en 3 agents séquentiels :

```
Agent 1 — Détection (déterministe)  →  Agent 2 — Analyse (LLM)  →  Agent 3 — Riposte (LLM)
```

Principe directeur (anti-hallucination) : tout ce qui est quantitatif (volume, vitesse, pic, identification des amplificateurs) est calculé par du code Python déterministe, jamais par un modèle de langage. Le LLM n'intervient que pour classer, résumer et rédiger, à partir des faits qui lui sont fournis, avec une sortie strictement typée (Pydantic), une température nulle, et la consigne explicite de répondre « non déterminable » si une information manque. Les agents LLM ne traitent pas l'intégralité du corpus, mais uniquement les événements déjà détectés par l'agent 1.

Deux modes d'exécution :

- **Batch** (`run_demo.py`) : traite le corpus entier d'un coup et produit jusqu'à `--max-events` fiches d'analyse et brouillons de riposte.
- **Temps réel simulé** (`run_stream.py`) : rejoue le corpus heure par heure, comme si les posts arrivaient en direct ; la détection ne connaît jamais que le passé, et le déclenchement des agents 2 et 3 est piloté par une politique configurable (`TriggerPolicy`).

Fournisseurs de modèle de langage pris en charge : Gemini (`GOOGLE_API_KEY`), Mistral (`MISTRAL_API_KEY`), ou un mode `mock` sans appel réel (utile pour valider la chaîne sans clé API). Voir `agents_cnc/README.md` pour le détail des commandes, de la configuration (`config.yaml`) et de la structure des modules.

Le chargeur de la phase 2 accepte également un CSV TweetClaw hors-ligne
contenant `createdAt`/`created_at` et `text`/`fullText`. Il le normalise vers
les colonnes du corpus interne, ce qui permet de tester la chaîne sur des
instantanés X/Twitter récents sans ajouter de collecte live ni de publication
automatique.

## Phase 3 — Monitoring & validation (`monitoring/`)

But : garantir qu'aucune riposte n'est publiée sans décision humaine. Un opérateur CNC consulte les événements détectés et, pour chacun, valide, édite, rejette (avec motif) ou demande un fact-check complémentaire.

Composants :

- **Backend** (`monitoring/backend/`) : API FastAPI exposant le tableau de bord (indicateurs clés, timeline, flux d'alertes), la file d'événements à valider, le détail de chaque événement, l'endpoint de décision de l'opérateur, et une piste d'audit. Les données proviennent d'un fichier `monitoring_seed.json`, généré par `build_seed.py` à partir du pipeline d'agents de la phase 2 (rejeu du corpus en mode temps réel simulé).
- **Frontend** (`monitoring/frontend/`) : tableau de bord en React, TypeScript et Tailwind CSS (avec Vite), affichant les indicateurs clés, une timeline de volume par heure, le flux d'alertes graduées et la file de validation avec panneau de décision.

Voir `monitoring/README.md` pour les commandes d'installation et de lancement du backend et du frontend, ainsi que le détail des routes de l'API.

## Le corpus (`data.xlsx`)

Le corpus est un export de social listening : 35 396 posts X/Twitter publiés en français, tous originaires de France, couvrant la période du 19 mars au 1ᵉʳ mai 2026 (42 jours), pour 10 437 auteurs uniques et un reach cumulé d'environ 77,8 millions.

Répartition par type de message (`Engagement Type`) :

| Type | Nombre de posts | Part |
|---|---|---|
| Retweet | 30 368 | 85,8 % |
| Réponse (reply) | 3 623 | 10,2 % |
| Citation (quote) | 734 | 2,1 % |
| Message original | 671 | 1,9 % |

Répartition par sentiment :

| Sentiment | Nombre de posts | Part |
|---|---|---|
| Neutre | 23 476 | 66,3 % |
| Négatif | 10 861 | 30,7 % |
| Positif | 1 059 | 3,0 % |

Le fichier `dictionnaire_bdd.xlsx` documente la définition exacte de chacune des 30 colonnes du corpus. Les colonnes les plus utilisées par les scripts et les agents sont les suivantes :

| Colonne | Rôle dans l'analyse |
|---|---|
| `Date` | Horodatage du post (`YYYY-MM-DD HH:MM:SS`), base de toute la chronologie. |
| `Author`, `X Author ID` | Identification de l'auteur du post. |
| `Full Text`, `message_normalizer` | Texte du post, brut puis nettoyé (minuscules, sans accents), utilisé pour la détection des angles narratifs. |
| `Engagement Type` | Nature du message : vide pour un message original, sinon `RETWEET`, `QUOTE` ou `REPLY`. |
| `X Repost of` | Auteur retweeté ; permet de reconstruire les cascades de diffusion et d'identifier les amplificateurs. |
| `Url` | URL du post, utilisée pour relier un retweet à son message d'origine. |
| `Likes`, `Comments`, `Shares`, `Impressions`, `Reach` | Indicateurs d'engagement et d'audience du post. |
| `X Followers`, `X Following`, `X Posts`, `X Verified` | Caractéristiques du compte auteur au moment du post (audience, ancienneté, certification). |
| `Sentiment` | Sentiment global du message, déjà labellisé dans le corpus. |
| `Hashtags` | Hashtags présents dans le message. |
| `postID`, `postDate` | Identifiant unique du post et date seule (sans l'heure). |

Quelques colonnes comportent une proportion significative de valeurs vides, par construction (et non par anomalie) : `Hashtags` (95,7 % de posts sans hashtag), `X Reply to` (89,8 %, rempli uniquement pour les réponses), `City` / `City Code` (50,6 %, dépendent du déclaratif de l'auteur), `Expanded URLs` (20,0 %) et `X Repost of` (14,2 %, rempli uniquement pour les retweets). Les scripts de la phase 1 et la fonction `load_corpus` de la phase 2 traitent ces vides de façon cohérente (par exemple, `Engagement Type` vide est interprété comme message original).

## Mise en route — vue d'ensemble des trois phases

Les commandes détaillées de chaque module figurent dans son propre README ; voici l'enchaînement global pour reproduire le projet de bout en bout.

```bash
# 1. Analyse descriptive (phase 1) — à la racine du dépôt
pip install -r requirements.txt
python analyse_corpus.py --input data.xlsx --outdir resultats

# 2. Chaîne d'agents IA (phase 2)
cd agents_cnc
pip install -r requirements.txt
python run_demo.py --input ../data.xlsx --provider mock      # sans clé API
# ou : python run_demo.py --input ../data.xlsx --provider gemini

# 3. Monitoring & validation (phase 3)
cd ../monitoring/backend
pip install -r requirements.txt
python build_seed.py                 # régénère monitoring_seed.json depuis le pipeline d'agents
uvicorn main:app --reload --port 8000

# dans un second terminal
cd ../frontend
npm install
npm run dev                            # tableau de bord sur http://localhost:5173
```

## Données et confidentialité

Le corpus (`data.xlsx`) contient des données d'auteurs de posts et n'est volontairement pas versionné dans ce dépôt (voir `.gitignore`) ; il doit être placé à la racine du projet, à côté de `analyse_corpus.py`, et récupéré séparément par les collaborateurs. Le fichier `dictionnaire_bdd.xlsx`, qui documente les colonnes du corpus, suit la même règle et n'est pas versionné non plus, bien qu'il ne contienne lui-même aucune donnée personnelle. De même, les résultats générés (dossier `resultats/`, fichiers `resultats_*.json`, `monitoring/backend/monitoring_seed.json`) ne sont pas versionnés : ils sont recalculés localement à partir du corpus.

Les clés API des fournisseurs de modèles de langage (Gemini, Mistral) ne doivent jamais être codées en dur ni versionnées : elles se configurent en variables d'environnement, à partir du modèle fourni dans `agents_cnc/.env.example`.

> Point d'attention : le fichier `agents_cnc/.env.example` fourni dans cette archive contient une valeur qui ressemble à une véritable clé API Google, et non un simple texte d'exemple. Il est recommandé de la révoquer immédiatement depuis la console du fournisseur concerné si elle a été utilisée, puis de remplacer ce fichier par un exemple neutre (par exemple `GOOGLE_API_KEY=votre_cle_ici`) avant toute publication ou tout partage du dépôt.

## Limites assumées (hors périmètre actuel)

- Pas de fact-check automatisé réel : il nécessiterait un corpus de sources officielles à interroger ; l'agent de riposte signale les affirmations à vérifier sans les trancher.
- Pas de collecte en temps réel depuis X : le mode « temps réel » de la phase 2 rejoue un dataset historique heure par heure, il ne lit pas un flux live.
- Pas de détection de bots fiable.

Ces briques sont décrites comme pistes d'évolution dans les supports `Agents_IA_CNC_methodologie.pptx` et `Phase2_Agents_IA_CNC.pptx`.
