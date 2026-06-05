import React, { useMemo, useState } from "react";

const SEV_COLOR = { ALTA: "#f44336", MEDIA: "#ff9800", BAIXA: "#4caf50" };
const CLS_LABEL = { foco_ativo: "Foco Ativo", fumaca: "Fumaça", area_queimada: "Área Queimada" };
const CLS_EMOJI = { foco_ativo: "🔥", fumaca: "💨", area_queimada: "🟫" };

function getSeverity(d) {
  if (d.severity) return d.severity;
  const c = parseFloat(d.confidence) || 0;
  if (c >= 0.92) return "ALTA";
  if (c >= 0.85) return "MEDIA";
  return "BAIXA";
}

function confBar(conf) {
  const pct   = Math.round((parseFloat(conf) || 0) * 100);
  const color = SEV_COLOR[getSeverity({ confidence: conf })] || "#555";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "3px" }}>
      <div style={{ flex: 1, height: "4px", background: "#2a2a2a", borderRadius: "2px" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: "2px" }} />
      </div>
      <span style={{ fontSize: "10px", color, fontWeight: 700, minWidth: "30px" }}>{pct}%</span>
    </div>
  );
}

function sourceLabel(det) {
  if (det.fonte) return det.fonte;
  const key = (det.image_key || "").toLowerCase();
  if (key.includes("modis"))    return "🛰 MODIS Terra";
  if (key.includes("sentinel")) return "🌍 Sentinel-2";
  if (key.includes("firms"))    return "📡 NASA FIRMS";
  if (key.includes("inpe"))     return "🇧🇷 IBAMA SISFOGO";
  return "🛰 Satélite";
}

function storyCard(detections, uniqueStatesCount) {
  const focos = detections.filter(d => d.class_name === "foco_ativo").length;
  const alta  = detections.filter(d => getSeverity(d) === "ALTA").length;
  const biomaCounts = {};
  detections.forEach(d => { if (d.bioma) biomaCounts[d.bioma] = (biomaCounts[d.bioma] || 0) + 1; });
  const topBioma = Object.entries(biomaCounts).sort((a, b) => b[1] - a[1])[0]?.[0];

  if (detections.length === 0) {
    return "Nenhum foco detectado no filtro atual. Aguardando próximo ciclo de satélite.";
  }
  let txt = `${focos} foco${focos !== 1 ? "s" : ""} ativo${focos !== 1 ? "s" : ""} em ${uniqueStatesCount || "—"} estado${uniqueStatesCount !== 1 ? "s" : ""}.`;
  if (alta > 0) txt += ` ${alta} de severidade ALTA.`;
  if (topBioma) txt += ` Bioma mais afetado: ${topBioma}.`;
  return txt;
}

const CLASS_CHIPS = [
  { value: null,           label: "Todos" },
  { value: "foco_ativo",   label: "🔥 Foco" },
  { value: "fumaca",       label: "💨 Fumaça" },
  { value: "area_queimada",label: "🟫 Queimada" },
];

const SEV_CHIPS = [
  { value: null,   label: "Todas" },
  { value: "ALTA", label: "ALTA",  color: SEV_COLOR.ALTA },
  { value: "MEDIA",label: "MEDIA", color: SEV_COLOR.MEDIA },
  { value: "BAIXA",label: "BAIXA", color: SEV_COLOR.BAIXA },
];

function Chip({ label, active, color, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "2px 8px", borderRadius: "8px", fontSize: "10px", fontWeight: 600,
        cursor: "pointer", border: `1px solid ${active ? (color || "#ff6b35") : "#333"}`,
        background: active ? `${color || "#ff6b35"}22` : "transparent",
        color: active ? (color || "#ff6b35") : "#555",
        transition: "all 0.12s",
      }}
    >
      {label}
    </button>
  );
}

export default function AlertPanel({
  stats = {}, alerts = [], detections = [],
  uniqueStatesCount = 0, focusedDetection,
  onFocusDetection, activeFilters = {}, onFilterChange,
  lastUpdated,
}) {
  const [tab, setTab]           = useState("detections");
  const [techOpen, setTechOpen] = useState(false);

  const items = tab === "alerts" ? alerts : detections;

  const narrative = useMemo(
    () => storyCard(detections, uniqueStatesCount),
    [detections, uniqueStatesCount]
  );

  return (
    <aside style={{
      width: "340px", background: "#111", borderLeft: "1px solid #222",
      display: "flex", flexDirection: "column", overflow: "hidden", flexShrink: 0,
    }}>

      {/* Stats grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1px", background: "#222", borderBottom: "1px solid #222" }}>
        <div style={{ background: "#111", padding: "12px 8px", textAlign: "center" }}>
          <div style={{ fontSize: "20px", fontWeight: 700, color: "#ff6b35" }}>{stats.total_focos ?? "—"}</div>
          <div style={{ fontSize: "9px", color: "#555", marginTop: "2px", textTransform: "uppercase", letterSpacing: "0.4px" }}>Focos 24h</div>
        </div>
        <div style={{ background: "#111", padding: "12px 8px", textAlign: "center" }}>
          <div style={{ fontSize: "20px", fontWeight: 700, color: "#ff6b35" }}>{uniqueStatesCount || "—"}</div>
          <div style={{ fontSize: "9px", color: "#555", marginTop: "2px", textTransform: "uppercase", letterSpacing: "0.4px" }}>Estados</div>
        </div>
        <div style={{ background: "#111", padding: "12px 8px", textAlign: "center" }}>
          <div style={{ fontSize: "20px", fontWeight: 700, color: "#ff6b35" }}>
            {stats.top_state && stats.top_state !== "BR" ? stats.top_state : "—"}
          </div>
          <div style={{ fontSize: "9px", color: "#555", marginTop: "2px", textTransform: "uppercase", letterSpacing: "0.4px" }}>Top Estado</div>
        </div>
      </div>

      {/* Storytelling card */}
      <div style={{ padding: "10px 14px", background: "#0d1117", borderBottom: "1px solid #1a1a1a" }}>
        <div style={{ fontSize: "11px", color: "#ccc", lineHeight: "1.6", fontStyle: "italic" }}>
          {narrative}
        </div>
        <button
          onClick={() => setTechOpen(o => !o)}
          style={{
            marginTop: "6px", background: "none", border: "none", cursor: "pointer",
            color: "#4caf50", fontSize: "10px", padding: 0,
          }}
        >
          {techOpen ? "▲ Ocultar detalhes técnicos" : "▼ Ver detalhes técnicos"}
        </button>
        {techOpen && (
          <div style={{ marginTop: "8px", fontSize: "10px", color: "#4caf50", lineHeight: "1.7" }}>
            <div>🤖 <b>YOLO v8n</b> — Object Detection · mAP50 = 0.902</div>
            <div>📊 Threshold: <b>75%</b> geral · <b>85%+</b> para alertas SNS</div>
            <div>🛰 Fontes: <b>NASA FIRMS</b> · <b>MODIS Terra</b> · <b>IBAMA</b></div>
            <div>⏱ Ciclo: <b>15 min</b> via AWS EventBridge</div>
            <div>☁ Lambda · DynamoDB · SNS · API Gateway</div>
          </div>
        )}
      </div>

      {/* Filter chips */}
      <div style={{ padding: "8px 14px", borderBottom: "1px solid #1a1a1a", display: "flex", flexDirection: "column", gap: "5px" }}>
        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
          {CLASS_CHIPS.map(c => (
            <Chip key={String(c.value)} label={c.label}
              active={activeFilters.class === c.value}
              onClick={() => onFilterChange("class", c.value)} />
          ))}
        </div>
        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
          {SEV_CHIPS.map(c => (
            <Chip key={String(c.value)} label={c.label} color={c.color}
              active={activeFilters.severity === c.value}
              onClick={() => onFilterChange("severity", c.value)} />
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid #222", flexShrink: 0 }}>
        {["detections", "alerts"].map(t => (
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
            {t === "alerts"
              ? `Alertas (${alerts.length})`
              : `Detecções (${detections.length})`
            }
          </button>
        ))}
      </div>

      {/* List */}
      <div style={{ overflowY: "auto", flex: 1 }}>
        {items.length === 0 ? (
          <div style={{ padding: "24px 14px", color: "#444", fontSize: "12px", textAlign: "center" }}>
            {tab === "alerts" ? "Nenhum alerta enviado" : "Nenhuma detecção no filtro atual"}
          </div>
        ) : (
          items.map((item) => {
            const sev         = getSeverity(item);
            const sevColor    = SEV_COLOR[sev];
            const src         = sourceLabel(item);
            const isFocused   = focusedDetection?.detection_id === item.detection_id;
            const ts          = item.timestamp ? new Date(item.timestamp) : null;
            const timeStr     = ts ? ts.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : null;
            const dateStr     = ts ? ts.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) : null;

            return (
              <div
                key={item.detection_id}
                onClick={() => onFocusDetection?.(item)}
                onMouseEnter={e => { if (!isFocused) e.currentTarget.style.background = "#191919"; }}
                onMouseLeave={e => { if (!isFocused) e.currentTarget.style.background = "transparent"; }}
                style={{
                  padding: "10px 14px", borderBottom: "1px solid #1a1a1a",
                  cursor: "pointer", transition: "background 0.12s",
                  background: isFocused ? "#1a1200" : "transparent",
                  borderLeft: isFocused ? "3px solid #ff6b35" : "3px solid transparent",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 600, color: "#f0f0f0" }}>
                    {CLS_EMOJI[item.class_name]} {CLS_LABEL[item.class_name] ?? item.class_name}
                  </span>
                  <span style={{
                    fontSize: "9px", fontWeight: 700, padding: "1px 6px", borderRadius: "4px",
                    color: sevColor, border: `1px solid ${sevColor}33`, background: `${sevColor}11`,
                  }}>
                    {sev}
                  </span>
                </div>

                {confBar(item.confidence)}

                {item.frp && parseFloat(item.frp) > 0 && (
                  <div style={{ fontSize: "10px", color: "#ff9800", marginTop: "2px" }}>
                    ⚡ FRP: {parseFloat(item.frp).toFixed(0)} MW
                  </div>
                )}

                <div style={{ fontSize: "10px", color: "#555", marginTop: "3px" }}>
                  📍 {item.state && item.state !== "BR" && item.state !== "UNKNOWN" ? item.state : "—"}
                  {item.bioma ? ` · ${item.bioma}` : ""}
                  {" · "}
                  {Number(item.latitude).toFixed(3)}, {Number(item.longitude).toFixed(3)}
                </div>

                {/* Alert timing info */}
                {tab === "alerts" ? (
                  <div style={{ marginTop: "3px", fontSize: "10px" }}>
                    {item.alert_sent ? (
                      <span style={{ color: "#4caf50" }}>
                        ✓ Alerta enviado{timeStr ? ` — detectado às ${timeStr} de ${dateStr}` : ""}
                        <span style={{ color: "#555" }}> (mesmo ciclo, ≤15 min)</span>
                      </span>
                    ) : (
                      <span style={{ color: "#555" }}>● Sem alerta (conf. abaixo do limiar)</span>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: "10px", color: "#555", marginTop: "3px" }}>
                    🕐 {timeStr && dateStr ? `${timeStr} · ${dateStr}` : "—"}
                    {item.alert_sent && (
                      <span style={{ color: "#4caf50", marginLeft: "6px" }}>✓ Alertado</span>
                    )}
                  </div>
                )}

                <div style={{ fontSize: "9px", color: "#4fc3f7", marginTop: "2px" }}>{src}</div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
