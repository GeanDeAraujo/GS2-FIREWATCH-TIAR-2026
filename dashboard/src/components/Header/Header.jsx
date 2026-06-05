import React from "react";

const s = {
  header: {
    display: "flex", alignItems: "center", gap: "12px",
    padding: "10px 20px", background: "#111", borderBottom: "1px solid #222",
    flexShrink: 0, flexWrap: "wrap",
  },
  logo: { fontSize: "22px" },
  title: { fontSize: "18px", fontWeight: 700, color: "#ff6b35" },
  subtitle: { fontSize: "11px", color: "#777", marginTop: "2px" },
  badges: { display: "flex", gap: "6px", marginLeft: "auto", flexWrap: "wrap", alignItems: "center" },
  badge: (color, bg) => ({
    padding: "3px 8px", borderRadius: "10px", fontSize: "10px", fontWeight: 600,
    color, background: bg, border: `1px solid ${color}33`,
  }),
  live: {
    padding: "3px 10px", borderRadius: "10px", fontSize: "11px", fontWeight: 600,
    background: "#1f2f1f", color: "#4caf50", border: "1px solid #2e4a2e",
  },
};

export default function Header({ lastUpdated, stats = {} }) {
  return (
    <header style={s.header}>
      <span style={s.logo}>🔥</span>
      <div>
        <div style={s.title}>FireWatch</div>
        <div style={s.subtitle}>Detecção de Incêndios via Satélite · FIAP 2026</div>
      </div>

      <div style={s.badges}>
        <span style={s.badge("#4fc3f7", "#0d2a38")}>🛰 NASA FIRMS</span>
        <span style={s.badge("#ce93d8", "#1e0d2a")}>🌍 MODIS Terra</span>
        <span style={s.badge("#a5d6a7", "#0d2a10")}>📡 IBAMA/SISFOGO</span>
        <span style={s.badge("#ffb74d", "#2a1a00")}>🤖 YOLO v8n</span>
        {stats.states_affected > 0 && (
          <span style={s.badge("#ef9a9a", "#2a0d0d")}>
            ⚠ {stats.states_affected} estado{stats.states_affected !== 1 ? "s" : ""}
          </span>
        )}
        <span style={s.live}>● LIVE{lastUpdated ? ` · ${lastUpdated}` : ""}</span>
      </div>
    </header>
  );
}
