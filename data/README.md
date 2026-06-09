# 📁 data — Dados do Projeto

O FireWatch **não versiona dados** no repositório. Todos os dados são obtidos em
tempo de execução, a partir de fontes externas, ou ficam em armazenamento na nuvem
(AWS S3 / DynamoDB). Esta pasta documenta de onde vêm e onde são consumidos.

## Fontes de dados externas

| Dado | Origem | Como é obtido | Consumido por |
|------|--------|---------------|---------------|
| Hotspots de calor (VIIRS/MODIS) | **NASA FIRMS** ([area API](https://firms.modaps.eosdis.nasa.gov/api/area/)) | API REST em runtime | `src/collectors/nasa_firms.py`, `src/collectors/inpe.py` |
| Tiles de imagem true-color | **NASA GIBS / MODIS Terra** (WMTS público) | API WMTS em runtime | `src/collectors/fetch_modis_tiles.py` |
| Imagens RGB+NIR multiespectrais | **Sentinel-2 / Copernicus** ([dataspace](https://dataspace.copernicus.eu/)) | OAuth + API em runtime | `src/collectors/sentinel2.py` |
| Dataset de treino (239 imagens anotadas) | **HuggingFace** [`Simuletic/CCTV-Smoke-Fire-Emergency-Detection-Dataset`](https://huggingface.co/datasets/Simuletic/CCTV-Smoke-Fire-Emergency-Detection-Dataset) | Download via `src/training/prepare_dataset.py` | Treino YOLO v8n |

## Onde os dados residem

- **Imagens brutas e CSVs de hotspots** → bucket **S3** (`raw/nasa_firms/`, `raw/modis/`), provisionado pelo Terraform.
- **Detecções processadas** → tabela **DynamoDB** (TTL de 90 dias).
- **Dataset de treino baixado** → `src/training/datasets/` (gitignored).
- **Pesos do modelo treinado** → S3 (`models/firewatch_yolov8.pt`); arquivos `.pt` locais são gitignored.

> Por isso esta pasta fica vazia no repositório: nada aqui é commitado. Veja
> [`../docs/arquitetura.md`](../docs/arquitetura.md) para o fluxo completo de dados.
