#!/usr/bin/env bash
# Build Docker image, push to ECR, and update both Lambda functions.
# Run from the repository root: bash lambda/build_and_push.sh
set -euo pipefail

REGION="${AWS_REGION:-sa-east-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="$(cd infrastructure && terraform output -raw ecr_repository_url)"
IMAGE_TAG="${1:-latest}"
FULL_URI="${ECR_REPO}:${IMAGE_TAG}"

echo "==> Building image: ${FULL_URI}"
# --platform linux/amd64: Lambda runs on x86; on Apple Silicon a plain build
#   would produce an arm64 image that Lambda rejects (Runtime.InvalidEntrypoint).
# --provenance=false: buildx otherwise emits a multi-arch manifest list; Lambda
#   requires a single-arch image manifest.
docker build --platform linux/amd64 --provenance=false -t "${FULL_URI}" lambda/

echo "==> Authenticating with ECR"
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "==> Pushing image"
docker push "${FULL_URI}"

# Bootstrap-safe: on the very first deploy the Lambda functions don't exist yet
# (Terraform can't create an Image-package function before the image is in ECR).
# In that case just push the image and let `terraform apply` create the functions.
PROCESSOR_FN="$(cd infrastructure && terraform output -raw lambda_processor_name 2>/dev/null || true)"
API_FN="$(cd infrastructure && terraform output -raw lambda_api_name 2>/dev/null || true)"

if [[ -z "${PROCESSOR_FN}" || -z "${API_FN}" ]]; then
  echo "==> Lambda functions not provisioned yet (first deploy)."
  echo "    Image pushed. Now run: (cd infrastructure && terraform apply)"
  exit 0
fi

echo "==> Updating Lambda: ${PROCESSOR_FN}"
aws lambda update-function-code \
  --function-name "${PROCESSOR_FN}" \
  --image-uri "${FULL_URI}" \
  --region "${REGION}"

echo "==> Updating Lambda: ${API_FN}"
aws lambda update-function-code \
  --function-name "${API_FN}" \
  --image-uri "${FULL_URI}" \
  --region "${REGION}"

echo "==> Done. Both Lambda functions updated to ${IMAGE_TAG}"
