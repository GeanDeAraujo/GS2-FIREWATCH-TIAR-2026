import React, { useState } from "react";

const SEV_COLOR = { ALTA: "#f44336", MEDIA: "#ff9800", BAIXA: "#4caf50" };
const CLS_LABEL = { foco_ativo: "Foco Ativo", fumaca: "Fumaça", area_queimada: "Área Queimada" };
const CLS_EMOJI = { foco_ativo: "🔥", fumaca: "💨", area_queimada: "🟫" };

function confToSev(conf) {
  const c = parseFloat(conf) || 0;
  if (c >= 0.92) return "ALTA";
  if (c >= 0.85) return "MEDIA";
  return "BAIXA";
}

function confBar(conf) {
  const pct = Math.round((parseFloat(conf) || 0) * 100);
  const color = SEV_COLOR[confToSev(conf)];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "3px" }}>
      <div style={{ flex: 1, height: "4px", background: "#2a2a2a", borderRadius: "2px" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: "2px" }} />
      </div>
      <span style={{ fontSize: "10px", color, fontWeight: 700, minWidth: "30px" }}>{pct}%</span>
    </div>
  );
}

const s = {
  panel: {
    width: "340px", background: "#111", borderLeft: "1px solid #222",
    display: "flex", flexDirection: "column", overflow: "hidden", flexShrink: 0,
  },
  statsGrid: {
    display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1px",
    background: "#222", borderBottom: "1px solid #222",
  },
  statCell: { background: "#111", padding: "12px 8px", textAlign: "center" },
  statVal:  { fontSize: "20px", fontWeight: 700, color: "#ff6b35" },
  statLbl:  { fontSize: "9px", color: "#555", marginTop: "2px", textTransform: "uppercase", letterSpacing: "0.4px" },
  techBox: {
    padding: "10px 14px", background: "#0d1a0d", borderBottom: "1px solid #1a2e1a",
    fontSize: "10px", color: "#4caf50", lineHeight: "1.7",
  },
  techTitle: { fontWeight: 700, marginBottom: "4px", color: "#81c784", fontSize: "11px" },
  listHeader: {
    padding: "10px 14px", fontSize: "11px", fontWeight: 600, color: "#777",
    textTransform: "uppercase", letterSpacing: "0.5px", borderBottom: "1px solid #1f1f1f",
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  list: { overflowY: "auto", flex: 1 },
  item: {
    padding: "10px 14px", borderBottom: "1px solid #1a1a1a",
    cursor: "pointer", transition: "background 0.12s",
  },
  itemTop:   { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" },
  className: { fontSize: "12px", fontWeight: 600, color: "#f0f0f0" },
  sevBadge:  (s) => ({
    fontSize: "9px", fontWeight: 700, padding: "1px 6px", borderRadius: "4px",
    color: SEV_COLOR[s] || "#888", border: `1px solid ${SEV_COLOR[s] || "#888"}33`,
    background: `${SEV_COLOR[s] || "#888"}11`,
  }),
  meta: { fontSize: "10px", color: "#555", marginTop: "3px" },
  sourceTag: { fontSize: "9px", color: "#4fc3f7", marginTop: "2px" },
  empty: { padding: "24px 14px", color: "#444", fontSize: "12px", textAlign: "center" },
};

function sourceLabel(imageKey) {
  if (!imageKey) return null;
  if (imageKey.includes("modis")) return "🛰 MODIS Terra";
  if (imageKey.includes("sentinel")) return "🌍 Sentinel-2";
  if (imageKey.includes("firms")) return "📡 NASA FIRMS";
  if (imageKey.includes("inpe")) return "🇧🇷 IBAMA SISFOGO";
  return "🛰 Satélite";
}

export default function AlertPanel({ stats = {}, alerts = [], detections = [], onAlertClick }) {
  const [tab, setTab] = useState("alerts");

  const items     = tab === "alerts" ? alerts : detections;
  const listTitle = tab === "alerts" ? `Alertas (${alerts.length})` : `Detecções (${detections.length})`;

  return (
    <aside style={s.panel}>

      {/* Stats grid */}
      <div style={s.statsGrid}>
        <div style={s.statCell}>
          <div style={s.statVal}>{stats.total_focos ?? "—"}</div>
          <div style={s.statLbl}>Focos Ativos</div>
        </div>
        <div style={s.statCell}>
          <div style={s.statVal}>{stats.states_affected ?? "—"}</div>
          <div style={s.statLbl}>Estados</div>
        </div>
        <div style={s.statCell}>
          <div style={s.statVal}>{stats.top_state ?? "—"}</div>
          <div style={s.statLbl}>Top Estado</div>
        </div>
      </div>

      {/* Tech info box */}
      <div style={s.techBox}>
        <div style={s.techTitle}>⚙ Tecnologia de Detecção</div>
        <div>🤖 <b>YOLO v8n</b> — Object Detection em tempo real</div>
        <div>📊 Limiar de confiança: <b>75%</b> · Alertas: <b>85%+</b></div>
        <div>🛰 Fontes: <b>NASA FIRMS</b> · <b>MODIS Terra</b> · <b>IBAMA SISFOGO</b></div>
        <div>⏱ Ciclo de atualização: <b>15 minutos</b> via EventBridge</div>
        <div>☁ <b>AWS Lambda</b> · <b>DynamoDB</b> · <b>SNS</b></div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #222" }}>
        {["alerts", "detections"].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              flex: 1, padding: "8px", border: "none", cursor: "pointer",
              background: tab === t ? "#1a1a1a" : "transparent",
              color: tab === t ? "#ff6b35" : "#555",
              fontSize: "11px", fontWeight: 600, textTransform: "uppercase",
              letterSpacing: "0.5px",
              borderBottom: tab === t ? "2px solid #ff6b35" : "2px solid transparent",
            }}
          >
            {t === "alerts" ? `Alertas (${alerts.length})` : `Detecções (${detections.length})`}
          </button>
        ))}
      </div>

      {/* List */}
      <div style={s.list}>
        {items.length === 0 ? (
          <div style={s.empty}>
            {tab === "alerts" ? "Nenhum alerta recente" : "Nenhuma detecção recente"}
          </div>
        ) : (
          items.map((item) => {
            const sev = confToSev(item.confidence);
            const src = sourceLabel(item.image_key);
            return (
              <div
                key={item.detection_id}
                style={s.item}
                onClick={() => onAlertClick?.(item)}
                onMouseEnter={e => e.currentTarget.style.background = "#191919"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                <div style={s.itemTop}>
                  <span style={s.className}>
                    {CLS_EMOJI[item.class_name]} {CLS_LABEL[item.class_name] ?? item.class_name}
                  </span>
                  <span style={s.sevBadge(sev)}>{sev}</span>
                </div>

                {confBar(item.confidence)}

                <div style={s.meta}>
                  📍 {item.state ?? "—"}
                  {item.bioma ? ` · ${item.bioma}` : ""}
                  {" · "}
                  {Number(item.latitude).toFixed(3)}, {Number(item.longitude).toFixed(3)}
                </div>
                <div style={s.meta}>
                  🕐 {item.timestamp ? new Date(item.timestamp).toLocaleString("pt-BR") : "—"}
                </div>
                {src && <div style={s.sourceTag}>{src}</div>}
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
