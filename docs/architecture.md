# Architecture du projet

## Vue d'ensemble

Le frontend est deploye sur Firebase Hosting.
Le backend tourne sur Cloud Run (GCP).

Les utilisateurs passent par Firebase Hosting -> Cloud Run -> Cloud SQL / GCS.

## Services GCP utilises

- Cloud Run : heberge l'API FastAPI
- Cloud SQL (PostgreSQL 15) : base de donnees, accessible uniquement depuis le VPC prive
- Cloud Storage : stockage des fichiers PDF, chiffres avec KMS
- Cloud KMS : gestion des cles de chiffrement, rotation tous les 30 jours
- Secret Manager : stocke les variables sensibles (DATABASE_URL, JWT_SECRET)
- VPC prive (jurydoc-vpc) : reseau isole, pas d'IP publique pour la base
- Cloud Monitoring : alertes en cas d'erreurs 403 repetees ou erreurs KMS
- Gemini 2.5 : resume automatique des documents

## Projet GCP

- Projet : any-safe-episen
- Region : europe-west9
- Firebase : anysafe-episen

## Deploiement (resume)

1. `cd terraform && terraform apply` pour creer l'infra
2. `docker build` + `gcloud run deploy` pour le backend
3. `npm run build` + `firebase deploy` pour le frontend
