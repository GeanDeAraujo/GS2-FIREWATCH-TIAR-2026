# 🧠 Modelo de Visão Computacional — YOLO v8n

## Classes detectadas

| Classe | Ícone no mapa | Descrição | Exemplos de fonte |
|--------|---------------|-----------|-------------------|
| `foco_ativo` | 🔴 Círculo com anel pulsante (ALTA) | Chamas visíveis / calor intenso | Câmeras, drones, imagens IR |
| `fumaca` | 🌫️ Nuvem cinza/azul | Pluma de fumaça em dispersão | Câmeras de longo alcance |
| `area_queimada` | 🟫 Quadrado marrom | Solo enegrecido pós-queima | Imagens de satélite |

## Processo de treinamento

O modelo foi treinado do zero — não havia nenhum modelo no projeto original:

1. **Dataset:** [`Simuletic/CCTV-Smoke-Fire-Emergency-Detection-Dataset`](https://huggingface.co/datasets/Simuletic/CCTV-Smoke-Fire-Emergency-Detection-Dataset) — 239 imagens anotadas (HuggingFace)
2. **Preparação:** `src/training/prepare_dataset.py` — organiza em splits YOLO (70/20/10), remapeia classes
3. **Treinamento:** 50 épocas, YOLOv8n, imgsz=640, batch=16 — hardware Apple M2 MPS
4. **Resultado:** mAP50 = **0.902** (focos e fumaça)
5. **Deploy:** modelo `.pt` enviado ao S3 (`models/firewatch_yolov8.pt`), Lambda baixa no cold start

## Tentativa de fine-tuning satelital

Após o treinamento base, tentamos um fine-tuning em imagens MODIS reais:

- **Script:** `src/training/build_satellite_dataset.py` — 119 tiles MODIS com 815 bounding boxes pseudo-label
- **Resultado:** mAP = 0.003 — inviável
- **Motivo:** YOLO detecta padrões visuais (textura, cor, forma). Em 250m/pixel, um foco é 1-2 pixels sem padrão reconhecível. Detecção satelital real exige bandas SWIR/NIR, não RGB.
- **Decisão:** manter modelo original (mAP=0.902) + pipeline FIRMS para dados satelitais
