# Deploiement

## 1. Infrastructure GCP (Terraform)

```bash
cd terraform
terraform init
terraform apply
```

Cree le VPC, Cloud SQL, Cloud Storage, Secret Manager, KMS et Cloud Run.

## 2. Backend sur Cloud Run

```bash
cd backend
docker build -t europe-west9-docker.pkg.dev/any-safe-episen/anysafe/api:latest .
docker push europe-west9-docker.pkg.dev/any-safe-episen/anysafe/api:latest

gcloud run deploy anysafe-api \
  --image europe-west9-docker.pkg.dev/any-safe-episen/anysafe/api:latest \
  --region europe-west9 \
  --project any-safe-episen \
  --no-allow-unauthenticated
```

## 3. Frontend sur Firebase Hosting

```bash
cd frontend
npm install
npm run build
firebase use anysafe-episen
firebase deploy --only hosting
```

Frontend accessible sur https://anysafe-episen.web.app

## Tests unitaires

```bash
GEMINI_API_KEY=mock_key PYTHONPATH=. pytest backend/test_main.py -v
```
