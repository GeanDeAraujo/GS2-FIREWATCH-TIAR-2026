# FIAP — Faculdade de Informática e Administração Paulista

<p align="center">
  <a href="https://www.fiap.com.br/">
    <img src="assets/architecture.png" alt="FireWatch — Arquitetura" width="70%">
  </a>
</p>

<br>

# 🔥 FireWatch — Sistema Inteligente de Detecção de Incêndios Florestais

> Plataforma serverless de monitoramento de incêndios em tempo real para o Brasil, integrando dados satelitais da NASA e INPE com visão computacional (YOLO v8) sobre infraestrutura AWS totalmente serverless.

---

## 📌 O Problema

O Brasil perde em média **2 a 4 horas** entre a ignição de um foco de incêndio e a notificação das autoridades. Nesse intervalo, um hectare pode virar dez. O FireWatch foi construído para fechar essa janela: processamento automático a cada 15 minutos, alertas diretos para Corpo de Bombeiros, IBAMA e Defesa Civil.

---

## 🏗️ Arquitetura — Pipeline Híbrido

O sistema usa **duas pipelines paralelas** que convergem no DynamoDB:

```
┌─────────────────────────────────────────────────────────────────┐
│  PIPELINE 1 — Hotspots Satelitais (NASA FIRMS)                  │
│                                                                 │
│  EventBridge (15 min)                                           │
│    → collectors/nasa_firms.py  →  S3 raw/nasa_firms/*.csv       │
│    → Lambda processor                                           │
│        → lê CSV  →  classifica por FRP (Fire Radiative Power)   │
│        → DynamoDB  →  SNS alert (se FRP ≥ 50 MW)               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PIPELINE 2 — Imagens → YOLO v8                                 │
│                                                                 │
│  collectors/fetch_modis_tiles.py  →  S3 raw/modis/*.jpg         │
│    → Lambda processor                                           │
│        → download imagem do S3                                  │
│        → YOLO v8n inference (confiança > 0.75)                  │
│        → DynamoDB  →  SNS alert                                 │
└─────────────────────────────────────────────────────────────────┘

                    ↓ (ambas pipelines)
              AWS DynamoDB
                    ↓
         API Gateway  →  Dashboard React + Leaflet.js
```

### Por que pipeline híbrida?

Durante o desenvolvimento, tentamos treinar o YOLO diretamente em imagens MODIS para detecção satelital — o mAP resultante foi 0.003 (inviável). A razão é física: imagens MODIS RGB têm resolução de 250m/pixel; um foco de incêndio ocupa 1-2 pixels e não tem textura visual detectável. Detecção satelital real requer bandas SWIR/NIR (infravermelho), não disponíveis no dataset MODIS RGB.

A solução híbrida é a mesma abordagem usada por sistemas reais: **FIRMS como ground-truth satelital** (já validado pela NASA) + **YOLO para câmeras/drones com imagens RGB**.

---

## 🛰️ Fontes de Dados

| Fonte | Status | O que oferece | Cobertura | Como acessar |
|-------|--------|---------------|-----------|--------------|
| **NASA FIRMS** | ✅ Ativo | Focos de calor VIIRS + MODIS | Global / Tempo real | [firms.modaps.eosdis.nasa.gov](https://firms.modaps.eosdis.nasa.gov/api/area/) |
| **NASA GIBS / MODIS Terra** | ✅ Ativo | Tiles de imagem true-color | Global | WMTS público |
| **IBAMA SISFOGO** | ⚠️ Parcial | Ocorrências por estado (sem lat/lon) | Brasil | CSV público aberto |
| **INPE BDQueimadas** | ❌ Offline | Focos históricos Brasil | Brasil | API em manutenção desde jun/2026 |
| **Sentinel-2 (Copernicus)** | ⚙️ Integrado | Imagens RGB+NIR multiespectrais | Global | [dataspace.copernicus.eu](https://dataspace.copernicus.eu/) |

> **Nota sobre INPE:** A API `queimadas.dgi.inpe.br/api/` retorna 404 desde junho/2026 (migração de endpoint). O `collectors/inpe.py` foi reescrito para usar a **NASA FIRMS área API** como fonte — o INPE usa os mesmos dados satelitais FIRMS internamente, então a atribuição permanece válida como "NASA FIRMS / INPE".

---

## 🧠 Modelo de Visão Computacional — YOLO v8n

### Classes detectadas

| Classe | Descrição | Exemplos de fonte |
|--------|-----------|-------------------|
| `foco_ativo` | Chamas visíveis / calor intenso | Câmeras, drones, imagens IR |
| `fumaca` | Pluma de fumaça em dispersão | Câmeras de longo alcance |
| `area_queimada` | Solo enegrecido pós-queima | Imagens de satélite |

### Processo de treinamento

O modelo foi treinado do zero — não havia nenhum modelo no projeto original:

1. **Dataset:** [`Simuletic/CCTV-Smoke-Fire-Emergency-Detection-Dataset`](https://huggingface.co/datasets/Simuletic/CCTV-Smoke-Fire-Emergency-Detection-Dataset) — 239 imagens anotadas (HuggingFace)
2. **Preparação:** `training/prepare_dataset.py` — organiza em splits YOLO (70/20/10), remapeia classes
3. **Treinamento:** 50 épocas, YOLOv8n, imgsz=640, batch=16 — hardware Apple M2 MPS
4. **Resultado:** mAP50 = **0.902** (focos e fumaça)
5. **Deploy:** modelo `.pt` enviado ao S3 (`models/firewatch_yolov8.pt`), Lambda baixa no cold start

### Tentativa de fine-tuning satelital

Após o treinamento base, tentamos um fine-tuning em imagens MODIS reais para que o YOLO detectasse focos diretamente nas tiles satelitais:

- **Script:** `training/build_satellite_dataset.py` — cria anotações pseudo-label a partir de coordenadas FIRMS em tiles MODIS (zoom 9, ~250m/pixel)
- **Dataset gerado:** 119 tiles com 815 bounding boxes
- **Resultado:** mAP = 0.003 — inviável
- **Motivo:** YOLO detecta padrões visuais (textura, cor, forma). Em resolução de 250m/pixel, um foco de incêndio é 1-2 pixels sem padrão visual reconhecível. Detecção satelital real usa algoritmos especializados em bandas SWIR/NIR (não RGB).
- **Decisão:** manter modelo original (mAP=0.902) + pipeline FIRMS para dados satelitais

Os scripts e configs estão mantidos em `training/` como documentação da abordagem.

---

## 🗂️ Estrutura do Projeto

```
FireWatch/
│
├── assets/
│   └── architecture.png              # Diagrama da arquitetura AWS
│
├── infrastructure/                   # Terraform — IaC para AWS
│   ├── main.tf                       # Provider AWS (sa-east-1) e backend
│   ├── variables.tf                  # Variáveis (região, nome, ambiente)
│   ├── outputs.tf                    # Outputs: ARNs, URLs, bucket name
│   ├── s3.tf                         # Bucket S3 para imagens brutas
│   ├── dynamodb.tf                   # Tabela detecções + GSI state-timestamp
│   ├── lambda.tf                     # 2 Lambdas Docker: processor + api
│   ├── ecr.tf                        # ECR repo para imagem Docker da Lambda
│   ├── eventbridge.tf                # Trigger cron a cada 15 minutos
│   ├── sns.tf                        # Tópico SNS para alertas
│   ├── api_gateway.tf                # REST API: /detections, /stats, /alerts
│   └── terraform.tfvars.example      # Template de variáveis (nunca commitar .tfvars)
│
├── lambda/
│   ├── Dockerfile                    # Imagem Docker (Amazon Linux 2, CPU-only PyTorch)
│   ├── requirements.txt              # ultralytics 8.4.60, boto3, Pillow, opencv-headless
│   ├── build_and_push.sh             # Script: build → ECR → update Lambda
│   └── processor/
│       ├── handler.py                # Entry point: pipeline híbrida FIRMS + YOLO
│       ├── api_handler.py            # Handler da Lambda API (routes: /detections /stats /alerts)
│       ├── detector.py               # Wrapper YOLO v8 — baixa modelo do S3 no cold start
│       ├── config.py                 # Env vars, thresholds, caminhos S3
│       └── services/
│           ├── dynamodb_service.py   # CRUD detecções, scan por estado/hora, stats agregadas
│           ├── s3_service.py         # Download de imagens do S3
│           └── sns_service.py        # Publicação de alertas no SNS
│
├── collectors/
│   ├── config.py                     # Configurações compartilhadas dos collectors
│   ├── nasa_firms.py                 # NASA FIRMS API — hotspots VIIRS/MODIS → S3 CSV
│   ├── inpe.py                       # INPE/FIRMS área BR — fallback após API INPE offline
│   ├── sentinel2.py                  # Sentinel-2 (Copernicus) — imagens RGB+NIR → S3
│   ├── fetch_modis_tiles.py          # NASA GIBS WMTS — tiles MODIS true-color → S3
│   ├── seed_demo_data.py             # Injeta 60 detecções demo no DynamoDB para apresentação
│   └── run_collectors.sh             # Script shell: roda todos os collectors sequencialmente
│
├── notifications/
│   ├── telegram_bot.py               # Bot Telegram para alertas à Defesa Civil
│   └── webhook_sender.py             # Webhook HTTP para notificação ao IBAMA
│
├── training/
│   ├── train.py                      # Script de treino YOLO v8n (50 épocas, M2 MPS)
│   ├── data.yaml                     # Config dataset principal (3 classes)
│   ├── data_satellite.yaml           # Config dataset satelital (fine-tuning — abandonado)
│   ├── prepare_dataset.py            # Organiza dataset HuggingFace em splits YOLO
│   ├── download_datasets.py          # Baixa datasets públicos (D-Fire, Roboflow)
│   ├── build_satellite_dataset.py    # Cria anotações pseudo-label de tiles MODIS + FIRMS
│   └── requirements.txt             # Dependências de treino (ultralytics, torch com MPS)
│
├── dashboard/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── App.jsx                   # Polling 72h, layout flex dark
│       ├── main.jsx
│       ├── services/
│       │   └── api.js                # fetchDetections / fetchStats / fetchAlerts → API Gateway
│       └── components/
│           ├── Header/
│           │   └── Header.jsx        # Badges: NASA FIRMS, MODIS, IBAMA, YOLO v8n, estados afetados
│           ├── Map/
│           │   ├── FireMap.jsx       # Mapa Leaflet com clustering de marcadores
│           │   └── FireMarker.jsx    # Popup: confiança %, severidade, modelo, técnica, estado, bioma
│           └── AlertPanel/
│               └── AlertPanel.jsx   # 2 abas (Alertas/Detecções), barra de confiança, info técnica
│
├── .env.example                      # Template — copie para .env e preencha
├── .gitignore
└── Readme.md
```

---

## ⚙️ Setup e Deploy

### Pré-requisitos

- Python 3.11+ (recomendado: `conda create -n firewatch python=3.11`)
- Node.js 18+
- Terraform 1.5+
- Docker Desktop
- AWS CLI configurado (`aws configure`)
- Conta AWS com permissões: S3, Lambda, ECR, DynamoDB, SNS, EventBridge, API Gateway, IAM

### 1. Clone e configure variáveis

```bash
git clone <repo-url>
cd FireWatch
cp .env.example .env
# Edite .env com suas credenciais (nunca commitar este arquivo)
```

### 2. Provisione a infraestrutura AWS com Terraform

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars
# Edite terraform.tfvars com seu projeto e ambiente

terraform init
terraform plan
terraform apply
```

Anote os outputs: `api_gateway_url`, `s3_bucket_name`, `dynamodb_table_name`, `sns_topic_arn`.

### 3. Treine o modelo YOLO (ou use o existente no S3)

Se quiser treinar do zero:

```bash
cd training
pip install -r requirements.txt
python prepare_dataset.py      # baixa e organiza o dataset
python train.py                # treina 50 épocas (~30 min no M2 MPS)
aws s3 cp runs/train/firewatch_v1/weights/best.pt \
    s3://<SEU_BUCKET>/models/firewatch_yolov8.pt
```

> O modelo treinado fica no S3. A Lambda baixa automaticamente no cold start via `detector.py`.

### 4. Build e deploy da Lambda

```bash
cd lambda
chmod +x build_and_push.sh
./build_and_push.sh   # faz build linux/amd64, push ECR, update Lambda
```

O script usa `--provenance=false` para garantir imagem single-arch (requisito AWS Lambda).

### 5. Execute os collectors para popular dados

```bash
# Ativa o .env e roda todos os collectors
bash collectors/run_collectors.sh

# Ou individualmente:
source .env
python collectors/nasa_firms.py      # hotspots VIIRS → S3
python collectors/fetch_modis_tiles.py  # tiles MODIS → S3
python collectors/inpe.py            # focos INPE/FIRMS → S3
```

### 6. Invoque a Lambda manualmente (opcional)

```bash
aws lambda invoke \
  --function-name firewatch-processor-prod \
  --region sa-east-1 \
  --payload '{"source":"manual"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/out.json && cat /tmp/out.json
```

### 7. Inicie o dashboard

```bash
cd dashboard
# Crie dashboard/.env com a URL da API:
echo "VITE_API_BASE_URL=https://<seu-api-id>.execute-api.sa-east-1.amazonaws.com/prod" > .env
npm install
npm run dev
# Acesse http://localhost:3000
```

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
| `YOLO_CONFIDENCE_THRESHOLD` | Threshold de confiança (padrão: `0.75`) | Ajuste conforme necessidade |
| `YOLO_MODEL_S3_KEY` | Caminho do modelo no S3 | Ex: `models/firewatch_yolov8.pt` |

---

## 🧪 Classificação de Severidade (Pipeline FIRMS)

Hotspots FIRMS são classificados por **FRP (Fire Radiative Power)** em megawatts:

| FRP | Classe | Severidade | Confiança |
|-----|--------|------------|-----------|
| ≥ 200 MW | `foco_ativo` | ALTA | ~0.92+ |
| 50–200 MW | `foco_ativo` | MEDIA | ~0.91 |
| < 50 MW | `fumaca` | BAIXA | 0.90 |

Fórmula de confiança: `min(0.99, 0.90 + frp / 10000)` — calibrada para FRP típico de incêndios no Cerrado e Amazônia.

---

## ❗ Decisões Técnicas e Limitações Conhecidas

| Decisão | Motivo |
|---------|--------|
| Pipeline FIRMS ao invés de YOLO para satelital | YOLO não funciona em imagens MODIS RGB (250m/pixel sem padrão visual) |
| CPU-only PyTorch na Lambda | Lambda não tem GPU; `--index-url .../whl/cpu` reduz imagem de ~2.5GB para ~933MB |
| Docker ao invés de .zip | `ultralytics` + `torch` + `opencv` excedem 250MB (limite do .zip Lambda) |
| `yum` ao invés de `dnf` no Dockerfile | Base Amazon Linux 2 usa `yum`; `dnf` não está disponível |
| `--provenance=false` no build Docker | Docker buildx cria manifest multi-arch que Lambda não suporta; flag força single-arch |
| INPE API substituída por FIRMS área | `queimadas.dgi.inpe.br/api/` retorna 404 desde jun/2026 (migração de endpoint) |
| `save_detection()` retorna `(id, timestamp)` | Lambda usava timestamps diferentes para save e mark_alert_sent, causando erro no update_item |
| `ultralytics==8.4.60` (não latest) | Versões > 8.2 com PyTorch 2.6 causavam `UnpicklingError` na Lambda até esta versão |

---

## 📡 API Endpoints

Base URL: configurada via `VITE_API_BASE_URL` / API Gateway

| Método | Endpoint | Descrição | Query Params |
|--------|----------|-----------|--------------|
| `GET` | `/detections` | Lista detecções recentes | `hours=72`, `limit=200`, `state=AM` |
| `GET` | `/stats` | Estatísticas agregadas 24h | — |
| `GET` | `/alerts` | Alertas disparados | `limit=20` |

Todos os endpoints retornam CORS headers para uso no dashboard.

---

## 🔬 Validação End-to-End

```bash
# 1. Verificar dados no DynamoDB (via API)
curl "https://<api-id>.execute-api.sa-east-1.amazonaws.com/prod/stats"

# 2. Ver últimas detecções
curl "https://<api-id>.execute-api.sa-east-1.amazonaws.com/prod/detections?hours=24&limit=5"

# 3. Invocar Lambda manualmente
aws lambda invoke \
  --function-name firewatch-processor-prod \
  --region sa-east-1 \
  --payload '{"source":"manual"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/result.json && cat /tmp/result.json
```

Resposta esperada:
```json
{
  "statusCode": 200,
  "body": {
    "firms_hotspots_added": 4484,
    "images_processed": 15,
    "alerts_sent": 0
  }
}
```

---

## 🚀 Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| IA / Visão Computacional | Python 3.11, YOLO v8n (Ultralytics 8.4.60), PyTorch 2.6 CPU |
| Cloud | AWS Lambda (Docker), S3, DynamoDB, SNS, EventBridge, API Gateway, ECR |
| IaC | Terraform 1.5+ |
| Containerização | Docker (linux/amd64, Amazon Linux 2) |
| Frontend | React 18, Vite, Leaflet.js |
| Dados Satelitais | NASA FIRMS (VIIRS/MODIS), NASA GIBS WMTS, Sentinel-2 (Copernicus) |

---

## 👥 Integrantes do Grupo

| Nome | RM | Turma |
|------|----|-------|
| — | — | — |

## 👨‍🏫 Professores

- **Tutor:** —
- **Coordenador:** —

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1">

Projeto acadêmico desenvolvido para a **FIAP** sob licença [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/).
