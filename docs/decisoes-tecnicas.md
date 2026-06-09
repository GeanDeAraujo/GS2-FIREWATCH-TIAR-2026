# ❗ Decisões Técnicas e Limitações Conhecidas

| Decisão | Motivo |
|---------|--------|
| Pipeline FIRMS como ground-truth satelital | YOLO não funciona em MODIS RGB (250m/pixel, sem padrão visual detectável) |
| CPU-only PyTorch na Lambda | Lambda sem GPU; índice `/whl/cpu` reduz imagem de ~2.5 GB para ~933 MB |
| Docker ao invés de .zip | `ultralytics` + `torch` + `opencv` excedem 250 MB (limite .zip Lambda) |
| `yum` ao invés de `dnf` no Dockerfile | Base Amazon Linux 2 usa `yum`; `dnf` não existe |
| `--provenance=false` no build Docker | Docker buildx gera manifest multi-arch; Lambda exige single-arch |
| INPE API substituída por FIRMS área | `queimadas.dgi.inpe.br/api/` retorna 404 desde jun/2026 |
| `save_detection()` retorna `(id, timestamp, created)` | O flag `created` (do *conditional put*) diz ao chamador se o hotspot é novo, evitando reenvio de alerta SNS no reprocessamento |
| `ultralytics==8.4.60` (pin) | Versões > 8.2 com PyTorch 2.6 causavam `UnpicklingError` no cold start Lambda |
| Vite proxy `/api → API Gateway` | OPTIONS preflight retorna 403 da API ao vivo; proxy elimina cross-origin em dev |
| Estado calculado client-side no dashboard | `_lat_lon_to_state()` no Lambda retorna "BR" para coordenadas fora das regras simples |
| `detection_id` determinístico (`uuid5`) + *conditional put* idempotente | EventBridge relista os CSVs a cada 15 min; sem chave determinística os ~4484 hotspots seriam re-inseridos a cada ciclo, inflando estatísticas |
| Range key sentinela (epoch) p/ hotspots sem data parseável | Garante idempotência sem usar `now()` (que mudaria a cada execução); registros malformados não duplicam |
| TTL de 90 dias (`expires_at`) no DynamoDB | Expira detecções antigas automaticamente, contendo custo de armazenamento sem job de limpeza |
| `_scan_all()` com teto de páginas (`_MAX_SCAN_PAGES`) | `scan` aplica `Limit` antes do `FilterExpression`; paginação completa corrige a contagem, e o teto limita RCU/latência (timeout 30s da Lambda de API) |
| Trigger de redeploy do API Gateway por corpo dos recursos | Hashear os recursos inteiros (não só `.id`) re-deploya o stage em edições in-place de `uri`/`request_templates`/`authorization` |
| `Subject` do SNS em ASCII | SNS rejeita `Subject` não-ASCII (≤100 chars); em-dash trocado por hífen |
| Telegram `parse_mode=Markdown` (legado) | `MarkdownV2` exigiria escapar `. - ( ) %` no texto, retornando HTTP 400 |

---

## 🧪 Classificação de Severidade (Pipeline FIRMS)

Hotspots FIRMS são classificados por **FRP (Fire Radiative Power)** em megawatts:

| FRP | Classe | Severidade | Confiança |
|-----|--------|------------|-----------|
| ≥ 200 MW | `foco_ativo` | ALTA | ~0.92+ |
| 50–200 MW | `foco_ativo` | MEDIA | ~0.91 |
| < 50 MW | `fumaca` | BAIXA | 0.90 |

Fórmula: `min(0.99, 0.90 + frp / 10000)` — calibrada para FRP típico de incêndios no Cerrado e Amazônia.
