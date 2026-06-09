# FIAP — Faculdade de Informática e Administração Paulista

<p align="center">
  <a href="https://www.fiap.com.br/">
    <img src="assets/logo-fiap.png" alt="FIAP — Faculdade de Informática e Administração Paulista" width="40%">
  </a>
</p>

<br>

# 🔥 FireWatch — Sistema Inteligente de Detecção de Incêndios Florestais

## Grupo FireWatch — Global Solution 2026 (TIAR)

> Plataforma serverless de monitoramento de incêndios em tempo real para o Brasil, integrando dados satelitais da NASA e INPE com visão computacional (YOLO v8) sobre infraestrutura AWS totalmente serverless.

<p align="center">
  <img src="assets/architecture.png" alt="FireWatch — Arquitetura AWS" width="70%">
</p>

---

## 👨‍🎓 Integrantes

| Nome | RM | Turma |
|------|----|-------|
| Gean Junio Ferreira de Araujo | rm567167 | TIAR |
| Victor Copque dos Reis | rm566821 | TIAR |
| Victor Hugo Ferreira Rolim | rm568006 | TIAR |

## 👩‍🏫 Professores

### Tutora
- Ana Cristina dos Santos

### Coordenador
- André Godoi Chiovato

---

## 📜 Descrição

O Brasil perde em média **2 a 4 horas** entre a ignição de um foco de incêndio e a notificação das autoridades. Nesse intervalo, um hectare pode virar dez. O **FireWatch** foi construído para fechar essa janela: processamento automático a cada 15 minutos e alertas diretos para Corpo de Bombeiros, IBAMA e Defesa Civil.

A solução usa uma **pipeline híbrida**: focos de calor da **NASA FIRMS** (já validados pela NASA) como ground-truth satelital, combinados com um modelo de **visão computacional YOLO v8n** (mAP50 = 0.902) para detectar focos, fumaça e áreas queimadas em imagens RGB de câmeras e drones. Tudo roda em infraestrutura **AWS 100% serverless** (Lambda, S3, DynamoDB, SNS, EventBridge, API Gateway), provisionada via **Terraform**, com um dashboard **React + Leaflet** exibindo os focos em tempo real.

📖 Detalhes técnicos completos:
- [🏗️ Arquitetura — pipeline híbrido e fontes de dados](docs/arquitetura.md)
- [🧠 Modelo de Visão Computacional — YOLO v8n](docs/modelo-yolo.md)
- [🖥️ Dashboard — funcionalidades](docs/dashboard.md)
- [📡 API — endpoints e validação end-to-end](docs/api.md)
- [❗ Decisões técnicas e limitações conhecidas](docs/decisoes-tecnicas.md)

---

## 📁 Estrutura de pastas

```
FireWatch/
├── assets/        # Logo FIAP e diagrama de arquitetura
├── docs/          # Documentação técnica: arquitetura, modelo, dashboard, API, decisões, deploy
├── data/          # (Sem dados versionados) — descreve as fontes externas e onde os dados residem
├── src/           # Todo o código-fonte
│   ├── collectors/      # Coletores Python: NASA FIRMS, MODIS, Sentinel-2, INPE
│   ├── training/        # Treino YOLO v8n + scripts de dataset
│   ├── lambda/          # Lambda processor (Docker): pipeline FIRMS + inferência YOLO
│   ├── infrastructure/  # Terraform — IaC para toda a stack AWS
│   ├── notifications/   # Bot Telegram + webhooks (Defesa Civil / IBAMA)
│   └── dashboard/       # Front-end React + Vite + Leaflet
├── .env.example   # Template de variáveis de ambiente
├── .gitignore
└── README.md
```

- **`docs`**: documentação textual detalhada — arquitetura, estratégia de IA, decisões técnicas e diagramas.
- **`src`**: todo o código-fonte desenvolvido (Python, JS/React, Terraform, Docker), incluindo coletores, modelo, inferências e microsserviços.
- **`data`**: o projeto não versiona dados; consulta [`data/README.md`](data/README.md) para as fontes externas (NASA FIRMS, Sentinel-2, HuggingFace) e onde residem (S3/DynamoDB).
- **`README.md`**: este guia geral do projeto.

---

## 📎 Links e Observações

- **Decisões técnicas:** [`docs/decisoes-tecnicas.md`](docs/decisoes-tecnicas.md) documenta as escolhas de engenharia (por que pipeline híbrida, Docker na Lambda, idempotência, etc.) e as limitações conhecidas.
- **Competição:** projeto desenvolvido para a **Global Solution 2026** da FIAP. O grupo **aceita** participar de eventuais etapas/divulgações da competição.

### 🚀 Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| IA / Visão Computacional | Python 3.11, YOLO v8n (Ultralytics 8.4.60), PyTorch 2.6 CPU |
| Cloud | AWS Lambda (Docker), S3, DynamoDB, SNS, EventBridge, API Gateway, ECR |
| IaC | Terraform 1.5+ |
| Containerização | Docker (linux/amd64, Amazon Linux 2) |
| Frontend | React 18, Vite 5, Leaflet.js, react-leaflet |
| Dados Satelitais | NASA FIRMS (VIIRS/MODIS), NASA GIBS WMTS, Sentinel-2 (Copernicus) |

---

## 🔧 Como executar o código

### Pré-requisitos
- Python 3.11+ · Node.js 18+ · Terraform 1.5+ · Docker Desktop · AWS CLI configurado
- Conta AWS com permissões para S3, Lambda, ECR, DynamoDB, SNS, EventBridge, API Gateway e IAM

### Passo a passo resumido (a partir da raiz do repositório)

```bash
# 1. Clone e configure as variáveis
git clone git@github.com:GeanDeAraujo/GS2-FIREWATCH-TIAR-2026.git
cd GS2-FIREWATCH-TIAR-2026
cp .env.example .env          # preencha suas credenciais

# 2. Provisione a infraestrutura AWS
cd src/infrastructure
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply -target=aws_ecr_repository.lambda_processor   # bootstrap do ECR
cd ../..

# 3. Build e push da imagem da Lambda
bash src/lambda/build_and_push.sh
cd src/infrastructure && terraform apply && cd ../..           # cria o restante da stack

# 4. Rode os collectors (popula o S3 com hotspots e imagens)
bash src/collectors/run_collectors.sh

# 5. Inicie o dashboard
cd src/dashboard
cp .env.example .env          # defina VITE_API_BASE_URL com a URL do API Gateway
npm install && npm run dev    # http://localhost:3000
```

📖 **Guia completo de setup, deploy e variáveis de ambiente:** [`docs/deploy.md`](docs/deploy.md)

---

## 🗃️ Histórico de lançamentos

* **0.4.0** — 09/06/2026
    * Dashboard interativo completo: filtros por satélite/classe/severidade, `flyTo`, ícones distintos por classe, storytelling dinâmico e proxy CORS via Vite.
* **0.3.0** — 05/06/2026
    * Pipeline híbrida idempotente: `detection_id` determinístico (`uuid5`) + *conditional put*; classificação de severidade por FRP; TTL de 90 dias no DynamoDB.
* **0.2.0** — 04/06/2026
    * Modelo YOLO v8n treinado (mAP50 = 0.902); Lambda processor em Docker; API Gateway com `/detections`, `/stats`, `/alerts`.
* **0.1.0** — 03/06/2026
    * Estrutura inicial: coletores NASA FIRMS / MODIS / Sentinel-2 e infraestrutura AWS em Terraform.

---

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1">

Projeto acadêmico desenvolvido para a **FIAP** sob licença [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/).
