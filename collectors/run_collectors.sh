#!/usr/bin/env bash
# Roda todos os collectors com as credenciais do .env
# Uso: bash collectors/run_collectors.sh
set -euo pipefail

if [ ! -f .env ]; then
  echo "ERRO: .env não encontrado. Crie o arquivo baseado em .env.example"
  exit 1
fi

set -a; source .env; set +a

PYTHON="/Users/geanjfa/anaconda3/envs/firewatch/bin/python"

echo "=== 1/3 NASA FIRMS (VIIRS hotspots) ==="
$PYTHON -c "
import sys; sys.path.insert(0,'collectors')
from nasa_firms import NASAFirmsCollector
import logging; logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
c = NASAFirmsCollector()
spots = c.fetch_hotspots(source='VIIRS_SNPP_NRT', days=1)
print(f'Hotspots: {len(spots)}')
if spots: c.upload_to_s3(spots, source='VIIRS_SNPP_NRT')
"

echo ""
echo "=== 2/3 Sentinel-2 (imagens satélite) ==="
$PYTHON -c "
import sys, os, tempfile; sys.path.insert(0,'collectors')
from sentinel2 import Sentinel2Collector
import logging; logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
c = Sentinel2Collector()
scenes = c.search_scenes(max_cloud_cover=20.0, max_results=3)
print(f'Cenas encontradas: {len(scenes)}')
for scene in scenes[:2]:
    with tempfile.TemporaryDirectory() as tmp:
        local = c.download_scene(scene, local_dir=tmp)
        key = c.upload_to_s3(local, scene, state='BR')
        print(f'Upload: {key}')
"

echo ""
echo "=== 3/3 INPE BDQueimadas ==="
$PYTHON -c "
import sys; sys.path.insert(0,'collectors')
from inpe import INPECollector
import logging; logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
c = INPECollector()
focos = c.fetch_focos(limit=500)
print(f'Focos INPE: {len(focos)}')
if focos: c.upload_to_s3(focos)
"

echo ""
echo "=== Collectors finalizados. Aguarde o EventBridge ou invoque manualmente: ==="
echo "aws lambda invoke --function-name firewatch-processor --region sa-east-1 \\"
echo "  --payload '{\"source\":\"manual\"}' --cli-binary-format raw-in-base64-out /tmp/out.json"
