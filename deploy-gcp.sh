#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="the-lab-488613"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-formatbench}"
REPOSITORY_NAME="${REPOSITORY_NAME:-formatbench}"
IMAGE_NAME="${IMAGE_NAME:-format-benchmarks}"
CPU="${CPU:-2}"
MEMORY="${MEMORY:-2Gi}"
CONCURRENCY="${CONCURRENCY:-1}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-900}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-3}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing .env file at ${ENV_FILE}"
  echo "Create it from .env.example and set GITLAB_PAT"
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

if [[ -z "${GITLAB_PAT:-}" ]]; then
  echo "GITLAB_PAT is not set in .env"
  exit 1
fi

echo "Setting gcloud project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}" >/dev/null

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com

echo "Ensuring Artifact Registry repository exists..."
if ! gcloud artifacts repositories describe "${REPOSITORY_NAME}" --location "${REGION}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${REPOSITORY_NAME}" \
    --repository-format docker \
    --location "${REGION}"
fi

echo "Creating/updating Secret Manager secret gitlab-pat from .env..."
if gcloud secrets describe gitlab-pat >/dev/null 2>&1; then
  printf "%s" "${GITLAB_PAT}" | gcloud secrets versions add gitlab-pat --data-file=- >/dev/null
else
  printf "%s" "${GITLAB_PAT}" | gcloud secrets create gitlab-pat --replication-policy=automatic --data-file=- >/dev/null
fi

echo "Granting Secret Manager access for Cloud Build service accounts..."
for sa in \
  "${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com" \
  "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"; do
  gcloud secrets add-iam-policy-binding gitlab-pat \
    --member="serviceAccount:${sa}" \
    --role="roles/secretmanager.secretAccessor" \
    --project "${PROJECT_ID}" >/dev/null
done

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${IMAGE_NAME}:latest"

echo "Mirroring image from GitLab to Artifact Registry (${IMAGE})..."
gcloud builds submit "${SCRIPT_DIR}" \
  --config "${SCRIPT_DIR}/cloudbuild-mirror.yaml" \
  --substitutions "_AR_IMAGE=${IMAGE}"

echo "Deploying Cloud Run service ${SERVICE_NAME}..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --cpu "${CPU}" \
  --memory "${MEMORY}" \
  --concurrency "${CONCURRENCY}" \
  --timeout "${TIMEOUT_SECONDS}" \
  --min-instances "${MIN_INSTANCES}" \
  --max-instances "${MAX_INSTANCES}" \
  --port 5000 \
  --set-env-vars ASPNETCORE_URLS=http://0.0.0.0:5000,Kestrel__Endpoints__Http__Url=http://0.0.0.0:5000

echo "Done. Service URL:"
gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format "value(status.url)"
