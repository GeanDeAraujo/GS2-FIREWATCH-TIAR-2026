# 📡 API Endpoints

Base URL: `VITE_API_BASE_URL` (dashboard) ou diretamente via curl.

| Método | Endpoint | Descrição | Query Params |
|--------|----------|-----------|--------------|
| `GET` | `/detections` | Detecções recentes | `hours=72`, `limit=200`, `state=AM` |
| `GET` | `/stats` | Estatísticas agregadas 24h | — |
| `GET` | `/alerts` | Alertas SNS enviados | `limit=20` |

---

## 🔬 Validação End-to-End

```bash
# Stats ao vivo
curl "https://<api-id>.execute-api.sa-east-1.amazonaws.com/prod/stats"
# → {"total_focos": 126, "top_state": "MT", "states_affected": 8, ...}

# Últimas detecções
curl "https://<api-id>.execute-api.sa-east-1.amazonaws.com/prod/detections?hours=24&limit=5"

# Invocar Lambda manualmente
aws lambda invoke \
  --function-name firewatch-processor-prod \
  --region sa-east-1 \
  --payload '{"source":"manual"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/result.json && cat /tmp/result.json
# → {"statusCode": 200, "body": {"firms_hotspots_added": 4484, "images_processed": 15, "alerts_sent": 0}}
```

> `firms_hotspots_added` conta apenas hotspots **novos**. Em uma segunda invocação sobre os mesmos CSVs o valor é `0` (idempotência via `detection_id` determinístico) — comprovando que o reprocessamento de 15 min não duplica registros.
