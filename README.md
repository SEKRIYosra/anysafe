# ANYSafe

Plateforme SaaS de gestion de documents juridiques pour cabinets d'avocats.

## Acces

- Frontend : https://anysafe-episen.web.app
- API (Swagger) : https://anysafe-api-xxxx-ew.a.run.app/docs

## Stack

- Frontend : React + Vite deploye sur Firebase Hosting
- Backend : FastAPI deploye sur Cloud Run (GCP)
- Base de donnees : Cloud SQL PostgreSQL 15
- Stockage : Cloud Storage chiffre avec KMS
- Infra : Terraform sur GCP europe-west9

## Fonctionnalites

- Authentification JWT avec 3 roles : Admin, Collaborateur, Auditeur
- Isolation des donnees par cabinet (multi-tenant)
- Upload et telechargement de documents PDF
- Logs d'audit de toutes les actions
- Simulateur d'attaques de securite (IDOR, RBAC, rate limiting...)

## Tests

```bash
GEMINI_API_KEY=mock_key PYTHONPATH=. pytest backend/test_main.py -v
```

## Deploiement

Voir docs/setup.md
