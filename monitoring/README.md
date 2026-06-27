# CNC — Monitoring & Validation des ripostes

Interface de supervision où le CNC **valide, édite, rejette ou demande un
fact-check** des ripostes proposées par les agents IA. *Human-in-the-loop* :
rien n'est publié sans décision humaine.

```
monitoring/
├── backend/   FastAPI : API événements + KPIs + timeline + alertes + décisions
└── frontend/  Vite + React + TypeScript + Tailwind : dashboard
```

## 1) Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt
# (option) régénérer les données depuis le pipeline d'agents :
python build_seed.py
uvicorn main:app --reload --port 8000
```

Endpoints :

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/dashboard` | KPIs + timeline + flux d'alertes |
| GET | `/api/events` | file de validation (résumés) |
| GET | `/api/events/{id}` | détail (fiche + riposte) |
| POST | `/api/events/{id}/decision` | décision : `validate` / `edit` / `reject` / `factcheck` |
| GET | `/api/audit` | piste d'audit |

Garde-fous : `reject` exige un motif, `edit` exige le texte édité (sinon 422).

## 2) Frontend (Vite + React + TS)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

L'URL de l'API se règle dans `.env` (`VITE_API_URL`, défaut `http://localhost:8000`).

### Le dashboard
- **KPIs** : événements détectés, en attente, reach, pic, posts, sentiment négatif.
- **Timeline** : volume de posts par heure (recharts).
- **Flux d'alertes** : alertes horodatées, graduées (faible/montée/crise).
- **File de validation** : chaque carte = un événement ; clic → panneau latéral.
- **Panneau riposte** : fiche de situation + brouillon **éditable** + actions
  Valider/Publier · Éditer puis valider · Rejeter (motif) · Demander un fact-check.

### UX / bonnes pratiques
TypeScript strict, composants découplés, client API typé, hook de données unique,
états loading/erreur/vide, accessibilité (rôles ARIA, focus visible, Échap pour
fermer), codes couleur de sévérité cohérents, validation des formulaires.

> Les données proviennent de `backend/monitoring_seed.json`, généré par le
> pipeline d'agents. Brancher un flux temps réel = remplacer la source du seed.
