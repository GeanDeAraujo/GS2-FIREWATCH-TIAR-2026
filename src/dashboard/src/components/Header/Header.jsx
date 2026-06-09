import React from "react";

const SAT_BADGES = [
  { key: "firms",    label: "NASA FIRMS",    emoji: "🛰",  color: "#4fc3f7", bg: "#0d2a38" },
  { key: "modis",    label: "MODIS Terra",   emoji: "🌍",  color: "#ce93d8", bg: "#1e0d2a" },
  { key: "sentinel", label: "Sentinel-2",    emoji: "📡",  color: "#a5d6a7", bg: "#0d2a10" },
  { key: "inpe",     label: "IBAMA/SISFOGO", emoji: "🇧🇷", color: "#ffb74d", bg: "#2a1a00" },
];

function story(stats, uniqueStatesCount, lastUpdated, activeSource) {
  const focos  = stats.total_focos;
  const top    = stats.top_state;

  if (!focos && focos !== 0) {
    return "Conectando aos satélites de monitoramento…";
  }

  let base = "";
  if (focos === 0) {
    base = "Nenhum foco ativo detectado no momento. O Brasil está limpo nas últimas 72h.";
  } else {
    const estadoStr = uniqueStatesCount > 0
      ? `em ${uniqueStatesCount} estado${uniqueStatesCount !== 1 ? "s" : ""}`
      : "no território nacional";
    const topStr = top && top !== "BR" && top !== "N/A"
      ? ` Estado mais afetado: ${top}.`
      : "";
    base = `${focos} foco${focos !== 1 ? "s" : ""} ativo${focos !== 1 ? "s" : ""} detectado${focos !== 1 ? "s" : ""} ${estadoStr} nas últimas 72h.${topStr}`;
  }

  if (activeSource) {
    const lbl = SAT_BADGES.find(b => b.key === activeSource)?.label || activeSource;
    base += ` Exibindo apenas dados de ${lbl}.`;
  }

  if (lastUpdated) base += ` Último ciclo às ${lastUpdated}.`;

  return base;
}

export default function Header({ lastUpdated, stats = {}, uniqueStatesCount = 0, activeFilters = {}, onFilterChange }) {
  const narrative = story(stats, uniqueStatesCount, lastUpdated, activeFilters.source);

  return (
    <header style={{
      padding: "10px 20px", background: "#111", borderBottom: "1px solid #222",
      flexShrink: 0,
    }}>
      {/* Top row */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "22px" }}>🔥</span>
        <div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#ff6b35" }}>FireWatch</div>
          <div style={{ fontSize: "10px", color: "#555" }}>Detecção de Incêndios via Satélite · FIAP 2026</div>
        </div>

        {/* Satellite filter buttons */}
        <div style={{ display: "flex", gap: "6px", marginLeft: "auto", flexWrap: "wrap", alignItems: "center" }}>
          {SAT_BADGES.map(b => {
            const active = activeFilters.source === b.key;
            return (
              <button
                key={b.key}
                onClick={() => onFilterChange("source", b.key)}
                title={active ? `Remover filtro ${b.label}` : `Filtrar por ${b.label}`}
                style={{
                  padding: "3px 9px", borderRadius: "10px", fontSize: "10px", fontWeight: 600,
                  color: b.color, background: active ? b.bg : "transparent",
                  border: `1px solid ${active ? b.color : b.color + "55"}`,
                  cursor: "pointer",
                  boxShadow: active ? `0 0 6px ${b.color}55` : "none",
                  transition: "all 0.15s",
                }}
              >
                {b.emoji} {b.label}
              </button>
            );
          })}

          <span style={{
            padding: "3px 8px", borderRadius: "10px", fontSize: "10px", fontWeight: 600,
            color: "#ffb74d", background: "#2a1a0033", border: "1px solid #ffb74d33",
          }}>
            🤖 YOLO v8n
          </span>

          {uniqueStatesCount > 0 && (
            <span style={{
              padding: "3px 8px", borderRadius: "10px", fontSize: "10px", fontWeight: 600,
              color: "#ef9a9a", background: "#2a0d0d", border: "1px solid #ef9a9a33",
            }}>
              ⚠ {uniqueStatesCount} estado{uniqueStatesCount !== 1 ? "s" : ""}
            </span>
          )}

          <span style={{
            padding: "3px 10px", borderRadius: "10px", fontSize: "11px", fontWeight: 600,
            background: "#1f2f1f", color: "#4caf50", border: "1px solid #2e4a2e",
          }}>
            ● LIVE{lastUpdated ? ` · ${lastUpdated}` : ""}
          </span>
        </div>
      </div>

      {/* Storytelling narrative */}
      <div style={{
        marginTop: "7px", fontSize: "11px", color: "#888", lineHeight: "1.5",
        borderTop: "1px solid #1a1a1a", paddingTop: "7px",
        fontStyle: "italic",
      }}>
        {narrative}
        {!activeFilters.source && (
          <span style={{ color: "#555" }}> Clique nos badges de satélite para filtrar por fonte.</span>
        )}
      </div>
    </header>
  );
}
