# 🏗️ Arquitetura — Pipeline Híbrido

<p align="center">
  <img src="../assets/architecture.png" alt="FireWatch — Arquitetura AWS" width="80%">
</p>

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

> **Idempotência:** como o EventBridge re-executa o processor a cada 15 min e ele relista os CSVs em `raw/`, cada hotspot FIRMS recebe um `detection_id` determinístico (`uuid5` de `fonte+lat+lon+FRP+data de aquisição`) gravado com *conditional put*. Reprocessar o mesmo foco é um no-op — sem duplicação no DynamoDB e sem reenvio de alerta SNS.

## Por que pipeline híbrida?

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

> **Nota sobre INPE:** A API `queimadas.dgi.inpe.br/api/` retorna 404 desde junho/2026 (migração de endpoint). O `src/collectors/inpe.py` foi reescrito para usar a **NASA FIRMS área API** como fonte — o INPE usa os mesmos dados satelitais FIRMS internamente, então a atribuição permanece válida como "NASA FIRMS / INPE".
