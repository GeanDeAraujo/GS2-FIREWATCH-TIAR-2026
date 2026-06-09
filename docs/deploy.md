# ⚙️ Setup e Deploy Completo

## Pré-requisitos

- Python 3.11+ (recomendado: `conda create -n firewatch python=3.11`)
- Node.js 18+
- Terraform 1.5+
- Docker Desktop
- AWS CLI configurado (`aws configure`)
- Conta AWS com permissões: S3, Lambda, ECR, DynamoDB, SNS, EventBridge, API Gateway, IAM

> Todos os comandos abaixo assumem que você está na **raiz do repositório**.

## 1. Clone e configure variáveis

```bash
git clone git@github.com:GeanDeAraujo/GS2-FIREWATCH-TIAR-2026.git
cd GS2-FIREWATCH-TIAR-2026
cp .env.example .env
# Edite .env com suas credenciais (nunca commitar este arquivo)
```

## 2. Provisione a infraestrutura AWS com Terraform

```bash
cd src/infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edite terraform.tfvars com seu projeto e ambiente

terraform init

# Bootstrap: as Lambdas usam package_type = "Image" e não podem ser criadas
# antes da imagem existir no ECR. Provisione primeiro só o repositório ECR:
terraform apply -target=aws_ecr_repository.lambda_processor
```

Em seguida faça o build/push da imagem (passo 4) e só então aplique o restante:

```bash
terraform apply   # cria Lambdas, API Gateway, DynamoDB, SNS, EventBridge…
```

Anote os outputs: `api_gateway_url`, `s3_bucket_name`, `dynamodb_table_name`, `sns_topic_arn`.

> **Ordem do primeiro deploy:** `terraform apply -target=aws_ecr_repository.lambda_processor` → `src/lambda/build_and_push.sh` (passo 4) → `terraform apply`. O `build_and_push.sh` detecta que as Lambdas ainda não existem, faz só o push e avisa para rodar o `terraform apply` final. Em deploys seguintes basta rodar `build_and_push.sh`, que atualiza o código das funções diretamente.

## 3. Treine o modelo YOLO (ou use o existente no S3)

```bash
cd src/training
pip install -r requirements.txt
python prepare_dataset.py      # baixa e organiza o dataset (~239 imagens)
python train.py                # 50 épocas (~30 min no M2 MPS)
aws s3 cp runs/train/firewatch_v1/weights/best.pt \
    s3://<SEU_BUCKET>/models/firewatch_yolov8.pt
```

> O modelo fica no S3. A Lambda baixa automaticamente no cold start via `detector.py`.

## 4. Build e deploy da Lambda

```bash
# A partir da raiz do repositório:
chmod +x src/lambda/build_and_push.sh
bash src/lambda/build_and_push.sh   # build linux/amd64, push ECR, update Lambda
```

O script usa `--provenance=false` para garantir imagem single-arch (requisito Lambda).

## 5. Execute os collectors

```bash
# A partir da raiz do repositório:
bash src/collectors/run_collectors.sh

# Ou individualmente:
source .env
python src/collectors/nasa_firms.py
python src/collectors/fetch_modis_tiles.py
python src/collectors/inpe.py
```

## 6. Invoque a Lambda manualmente (opcional)

```bash
aws lambda invoke \
  --function-name firewatch-processor-prod \
  --region sa-east-1 \
  --payload '{"source":"manual"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/out.json && cat /tmp/out.json
```

## 7. Inicie o dashboard

```bash
cd src/dashboard
cp .env.example .env
# Edite .env: VITE_API_BASE_URL=https://<seu-api-id>.execute-api.sa-east-1.amazonaws.com/prod
npm install
npm run dev
# Acesse http://localhost:3000
```

> O Vite usa proxy `/api → API Gateway`, então não há erro de CORS em desenvolvimento.

---

## 🔌 Variáveis de Ambiente

Copie `.env.example` para `.env` e preencha:

| Variável | Descrição | Onde obter |
|----------|-----------|------------|
| `AWS_REGION` | Região AWS (ex: `sa-east-1`) | Console AWS |
| `AWS_ACCESS_KEY_ID` | Credencial AWS | IAM → Usuários → Security credentials |
| `AWS_SECRET_ACCESS_KEY` | Credencial AWS | IAM → Usuários → Security credentials |
| `AWS_BUCKET_NAME` | Nome do bucket S3 | Output do `terraform apply` |
| `DYNAMODB_TABLE_NAME` | Nome da tabela DynamoDB | Output do `terraform apply` |
| `SNS_TOPIC_ARN` | ARN do tópico SNS | Output do `terraform apply` |
| `NASA_FIRMS_API_KEY` | Chave API NASA FIRMS | [firms.modaps.eosdis.nasa.gov/api/area/](https://firms.modaps.eosdis.nasa.gov/api/area/) |
| `SENTINEL_CLIENT_ID` | ID do app Copernicus | [dataspace.copernicus.eu](https://dataspace.copernicus.eu/) → My Account |
| `SENTINEL_CLIENT_SECRET` | Segredo do app Copernicus | [dataspace.copernicus.eu](https://dataspace.copernicus.eu/) → My Account |
| `TELEGRAM_BOT_TOKEN` | Token do bot Telegram | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `TELEGRAM_CHAT_ID` | ID do chat para alertas | `https://api.telegram.org/bot<TOKEN>/getUpdates` |
| `YOLO_CONFIDENCE_THRESHOLD` | Threshold de confiança (padrão: `0.75`) | — |
| `YOLO_MODEL_S3_KEY` | Caminho do modelo no S3 | Ex: `models/firewatch_yolov8.pt` |
