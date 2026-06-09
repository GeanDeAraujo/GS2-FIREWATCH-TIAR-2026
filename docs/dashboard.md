# 🖥️ Dashboard — Funcionalidades

O dashboard React exibe dados em tempo real com interatividade completa.

## Navegação mapa ↔ lista
- **Clique num item da lista** → mapa voa automaticamente (`flyTo`) para o foco com zoom 10 e abre o popup
- **Clique num marcador no mapa** → seleciona o item correspondente na lista lateral (borda laranja)

## Filtros por satélite (Header)
Os badges de satélite são botões de filtro com toggle:

| Badge | Filtra por |
|-------|-----------|
| 🛰 NASA FIRMS | Hotspots CSV do FIRMS |
| 🌍 MODIS Terra | Tiles de imagem MODIS |
| 📡 Sentinel-2 | Imagens Copernicus |
| 🇧🇷 IBAMA/SISFOGO | Dados IBAMA |

## Filtros inline no painel
- **Por classe:** Todos | 🔥 Foco | 💨 Fumaça | 🟫 Queimada
- **Por severidade:** Todas | ALTA | MEDIA | BAIXA
- Todos os filtros são combinados e se aplicam simultaneamente ao mapa e à lista

## Diferenciação visual no mapa
- `foco_ativo` ALTA → círculo vermelho com **anel pulsante animado** (CSS `@keyframes`)
- `foco_ativo` MEDIA/BAIXA → círculo sólido laranja/amarelo
- `fumaca` → **ícone de nuvem** cinza/azul distinto (SVG com elipses)
- `area_queimada` → quadrado marrom com X hachurado

## Informações de alerta
- Cada detecção mostra se alerta SNS foi enviado (`✓ Alertado`)
- Aba Alertas exibe: horário de detecção + "mesmo ciclo (≤ 15 min)"
- FRP (Fire Radiative Power em MW) exibido para hotspots FIRMS

## Storytelling dinâmico
- Header e painel lateral exibem narrativa contextual baseada nos dados ao vivo
- Exemplo: *"126 focos ativos detectados em 8 estados nas últimas 72h. Estado mais afetado: MT. Último ciclo às 14:32."*
