# Agents IA — Veille & Riposte CNC (test phase 2)

Chaîne de **3 agents** testée sur le corpus de la polémique CNC (35 396 posts).

```
Détection (déterministe)  →  Analyse (LLM)  →  Riposte (LLM)
```

## Principe directeur (anti-hallucination)

- Tout ce qui est **quantitatif** (volume, vitesse, pic, amplificateurs) est calculé en **Python déterministe** : exact, reproductible, impossible à inventer.
- Le **LLM** n'intervient que pour **classer / résumer / rédiger**, et il est encadré :
  - sortie **typée** (`pydantic` + `with_structured_output`) ;
  - **ancrage strict** : l'agent ne voit que les faits fournis ;
  - consigne « **non déterminable** » si l'info manque ;
  - `temperature = 0`.
- Les agents LLM ne tournent **pas** sur les 35 k posts, mais seulement sur les **événements détectés** (peu d'appels, coût maîtrisé).

## Installation

```bash
pip install -r requirements.txt
```

## Configuration du LLM

Choisis **Gemini** ou **Mistral** et fournis la clé correspondante :

```bash
export GOOGLE_API_KEY=...      # Gemini
# ou
export MISTRAL_API_KEY=...     # Mistral
```

(voir `.env.example`)

## Lancer

```bash
# Sans clé : agent 1 réel + agents 2/3 en repli déterministe (validation de la chaîne)
python run_demo.py --input ../data.xlsx --provider mock

# Avec Gemini
python run_demo.py --input ../data.xlsx --provider gemini --max-events 2

# Avec Mistral
python run_demo.py --input ../data.xlsx --provider mistral
```

Sortie : un résumé console + `resultats_agents.json` (détection + fiches + brouillons de riposte).

## Structure

| Fichier | Rôle |
|---|---|
| `config.py` | Réglages, seuils de détection, **fabrique de modèles** (gemini/mistral/mock) |
| `data_loader.py` | Chargement & nettoyage du corpus |
| `schemas.py` | Contrats Pydantic échangés entre agents |
| `agents/detection_agent.py` | **Agent 1** — veille déterministe |
| `agents/analysis_agent.py` | **Agent 2** — fiche de situation (LLM) |
| `agents/riposte_agent.py` | **Agent 3** — brouillon de riposte (LLM) |
| `orchestrator.py` | Enchaînement des 3 agents |
| `run_demo.py` | Point d'entrée CLI |

## Évaluation (vérité terrain)

Le corpus contient une crise connue : l'agent de détection **doit** s'allumer autour du **pic du 26/03 (751 posts/h)** mesuré en phase 1. C'est le test de non-régression.

## Hors périmètre de ce test (assumé)

Pas de **fact-check** réel (il faudrait un corpus de sources officielles), pas de **collecte temps réel** (dataset statique), pas de **détection de bots** fiable. Ces briques sont décrites dans le deck *Phase 2*.

## Mode TEMPS RÉEL (rejeu du dataset)

Au lieu de tout traiter d'un coup, `run_stream.py` fait défiler le corpus
**heure simulée par heure simulée**. La détection est **incrémentale** : à chaque
instant elle ne connaît que le **passé**. Dès qu'un emballement franchit le seuil
« montée », l'analyse et la riposte se déclenchent **sur le moment**.

```bash
# Aussi vite que possible
python run_stream.py --input ../data.xlsx --provider mock

# Ralenti pour "voir" le flux défiler (0.02 s par heure simulée)
python run_stream.py --input ../data.xlsx --provider mock --hour-delay 0.02
```

Sortie : flux d'alertes horodatées + `resultats_stream.json`. Détail clé : au
déclenchement, l'événement n'est assemblé qu'à partir des posts **déjà connus**
(ex. pic vu = 130 posts/h à 09:00, alors que le pic réel de 751 n'arrivera qu'à 16:00).

> *Simulation* fondée sur des données historiques : le « temps réel » est reconstitué
> en rejouant les horodatages, pas en interrogeant X en direct.

## Configuration générique (config.yaml)

Toute la config non-secrète vit dans `config.yaml`, **validée par Pydantic**
(`AppConfig`). Elle est scindée en deux couches :

| Couche | Sections | Réutilisable ? |
|---|---|---|
| **Générique** | `llm`, `runtime`, `trigger` | Oui — telle quelle pour tout projet d'agents |
| **Domaine (CNC)** | `detection` (seuils, narratifs) | Non — à adapter par problème |

Pour un **autre problème d'agents**, on garde la couche générique et on ne
remplace que la section `detection` (+ les schémas/prompts du domaine).
Les **secrets** (clés API) ne sont jamais dans le YAML : ils restent en
variables d'environnement.

### Politique de déclenchement (`trigger`)

C'est elle qui décide **quand** lancer les agents en aval, indépendamment de la
détection :

```yaml
trigger:
  mode: on_threshold      # on_threshold = 1 fois au franchissement ; on_escalation = à chaque palier
  min_level: montee       # sévérité minimale pour déclencher (faible|montee|crise)
  once_per_event: true    # anti-rebond : un seul déclenchement par événement (mode on_threshold)
  cooldown_min: 0         # délai minimal entre deux déclenchements
```

- `on_threshold` : déclenche **une fois**, la première fois que l'événement atteint `min_level`.
- `on_escalation` : **re-déclenche** à chaque montée vers un palier supérieur (ex. faible -> crise).

La logique est dans `triggers.py` (`TriggerPolicy.should_fire`) — générique, pilotée par la config.

### Surcharge en ligne de commande

```bash
python run_stream.py --input ../data.xlsx --provider gemini      # surcharge llm.provider
python run_stream.py --input ../data.xlsx --config autre.yaml    # autre fichier de config
```
