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
docker build -t "${FULL_URI}" lambda/

echo "==> Authenticating with ECR"
aws ecr get-login-password --region "${REGION}" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

echo "==> Pushing image"
docker push "${FULL_URI}"

PROCESSOR_FN="$(cd infrastructure && terraform output -raw lambda_processor_name)"
API_FN="$(cd infrastructure && terraform output -raw lambda_api_name)"

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
