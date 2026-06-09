import { divIcon } from "leaflet";
import React, { useEffect, useRef } from "react";
import { Marker, Popup, useMap } from "react-leaflet";

const SEV_COLOR  = { ALTA: "#f44336", MEDIA: "#ff9800", BAIXA: "#4caf50" };
const CLS_EMOJI  = { foco_ativo: "🔥", fumaca: "💨", area_queimada: "🟫" };
const CLS_LABEL  = { foco_ativo: "Foco Ativo", fumaca: "Fumaça", area_queimada: "Área Queimada" };
const BIOMA_ICON = {
  "Amazônia": "🌳", "Cerrado": "🌿", "Pantanal": "🐊",
  "Caatinga": "🌵", "Mata Atlântica": "🌲", "Pampa": "🌾",
};

// Injects pulse keyframes once into the document
let pulseInjected = false;
function injectPulse() {
  if (pulseInjected || typeof document === "undefined") return;
  const style = document.createElement("style");
  style.textContent = `
    @keyframes fw-pulse {
      0%   { transform: scale(1);   opacity: 0.9; }
      50%  { transform: scale(1.6); opacity: 0.3; }
      100% { transform: scale(1);   opacity: 0.9; }
    }
    .fw-pulse-ring {
      animation: fw-pulse 1.6s ease-in-out infinite;
      transform-origin: center;
    }
  `;
  document.head.appendChild(style);
  pulseInjected = true;
}

function classifyConf(conf) {
  const c = parseFloat(conf) || 0;
  if (c >= 0.92) return "ALTA";
  if (c >= 0.85) return "MEDIA";
  return "BAIXA";
}

function makeIcon(conf, cls, focused) {
  injectPulse();
  const sev   = classifyConf(conf);
  const color = SEV_COLOR[sev];
  const focusBorder = focused ? `stroke="#fff" stroke-width="3"` : `stroke="white" stroke-width="1.5"`;

  if (cls === "foco_ativo") {
    const size  = sev === "ALTA" ? 24 : 20;
    const pulse = sev === "ALTA"
      ? `<circle cx="12" cy="12" r="10" fill="${color}" fill-opacity="0.25" class="fw-pulse-ring"/>`
      : "";
    // Flame-like SVG
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">
      ${pulse}
      <circle cx="12" cy="12" r="8" fill="${color}" fill-opacity="0.9" ${focusBorder}/>
      <circle cx="12" cy="12" r="3.5" fill="white" fill-opacity="0.8"/>
    </svg>`;
    return divIcon({ html: svg, className: "", iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
  }

  if (cls === "fumaca") {
    // Smoke cloud SVG — gray/blue, softer
    const smokeColor = focused ? "#90caf9" : "#78909c";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="16" viewBox="0 0 32 24">
      <ellipse cx="12" cy="14" rx="8"  ry="6"  fill="${smokeColor}" fill-opacity="0.75"/>
      <ellipse cx="18" cy="12" rx="7"  ry="5"  fill="${smokeColor}" fill-opacity="0.65"/>
      <ellipse cx="8"  cy="12" rx="6"  ry="4.5" fill="${smokeColor}" fill-opacity="0.55"/>
      <ellipse cx="14" cy="9"  rx="5"  ry="4"  fill="${smokeColor}" fill-opacity="0.6"/>
      ${focused ? `<ellipse cx="13" cy="12" rx="12" ry="8" fill="none" stroke="#90caf9" stroke-width="1.5" fill-opacity="0"/>` : ""}
    </svg>`;
    return divIcon({ html: svg, className: "", iconSize: [20, 16], iconAnchor: [10, 8] });
  }

  // area_queimada — dark brown square
  const burnColor = focused ? "#a1887f" : "#6d4c41";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24">
    <rect x="3" y="3" width="18" height="18" rx="3" fill="${burnColor}" fill-opacity="0.8"
      stroke="${focused ? "white" : burnColor}" stroke-width="${focused ? 2 : 1}"/>
    <line x1="7" y1="7" x2="17" y2="17" stroke="#3e2723" stroke-width="1.5"/>
    <line x1="17" y1="7" x2="7"  y2="17" stroke="#3e2723" stroke-width="1.5"/>
  </svg>`;
  return divIcon({ html: svg, className: "", iconSize: [16, 16], iconAnchor: [8, 8] });
}

function sourceFromKey(det) {
  const key = (det.image_key || "").toLowerCase();
  if (det.fonte) return det.fonte;
  if (key.includes("modis"))    return "MODIS Terra (NASA GIBS)";
  if (key.includes("sentinel")) return "Sentinel-2 (Copernicus)";
  if (key.includes("firms"))    return "NASA FIRMS";
  if (key.includes("inpe"))     return "IBAMA / SISFOGO";
  return "Satélite";
}

// Subcomponent that auto-opens popup when focused
function MarkerInner({ detection, focused, onClick }) {
  const markerRef = useRef(null);
  const { latitude, longitude, class_name, confidence, timestamp, state, bioma, frp } = detection;
  const lat = parseFloat(latitude);
  const lon = parseFloat(longitude);

  useEffect(() => {
    if (focused && markerRef.current) {
      markerRef.current.openPopup();
    }
  }, [focused]);

  // Hooks acima de qualquer return condicional (regras de hooks do React).
  if (isNaN(lat) || isNaN(lon)) return null;

  const conf      = parseFloat(confidence) || 0;
  const sev       = classifyConf(conf);
  const sevColor  = SEV_COLOR[sev];
  const fonte     = sourceFromKey(detection);
  const biomaIcon = BIOMA_ICON[bioma] || "🌿";

  return (
    <Marker
      ref={markerRef}
      position={[lat, lon]}
      icon={makeIcon(confidence, class_name, focused)}
      eventHandlers={{ click: () => onClick?.(detection) }}
      zIndexOffset={focused ? 1000 : 0}
    >
      <Popup maxWidth={270} autoPan={false}>
        <div style={{ minWidth: "230px", fontFamily: "system-ui, sans-serif", fontSize: "12px", lineHeight: "1.6" }}>

          <div style={{ fontWeight: 700, fontSize: "14px", color: sevColor, marginBottom: "6px" }}>
            {CLS_EMOJI[class_name]} {CLS_LABEL[class_name] ?? class_name}
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "6px" }}>
            <tbody>
              <tr>
                <td style={{ color: "#888", paddingRight: "8px" }}>Confiança</td>
                <td style={{ fontWeight: 700, color: sevColor }}>{(conf * 100).toFixed(1)}%</td>
              </tr>
              <tr>
                <td style={{ color: "#888" }}>Severidade</td>
                <td style={{ fontWeight: 700, color: sevColor }}>{sev}</td>
              </tr>
              {frp && parseFloat(frp) > 0 && (
                <tr>
                  <td style={{ color: "#888" }}>FRP</td>
                  <td style={{ fontWeight: 600 }}>{parseFloat(frp).toFixed(0)} MW</td>
                </tr>
              )}
              <tr>
                <td style={{ color: "#888" }}>Modelo</td>
                <td>YOLO v8n · FireWatch</td>
              </tr>
              <tr>
                <td style={{ color: "#888" }}>Técnica</td>
                <td>Object Detection</td>
              </tr>
            </tbody>
          </table>

          <hr style={{ border: "none", borderTop: "1px solid #eee", margin: "6px 0" }} />

          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <tbody>
              <tr>
                <td style={{ color: "#888", paddingRight: "8px" }}>Estado</td>
                <td style={{ fontWeight: 600 }}>{state ?? "—"}</td>
              </tr>
              {bioma && (
                <tr>
                  <td style={{ color: "#888" }}>Bioma</td>
                  <td>{biomaIcon} {bioma}</td>
                </tr>
              )}
              <tr>
                <td style={{ color: "#888" }}>Coordenadas</td>
                <td style={{ fontFamily: "monospace", fontSize: "11px" }}>{lat.toFixed(4)}, {lon.toFixed(4)}</td>
              </tr>
              <tr>
                <td style={{ color: "#888" }}>Fonte</td>
                <td style={{ fontSize: "11px" }}>{fonte}</td>
              </tr>
              {detection.alert_sent && (
                <tr>
                  <td style={{ color: "#888" }}>Alerta</td>
                  <td style={{ color: "#4caf50", fontSize: "11px" }}>✓ Enviado (≤15 min)</td>
                </tr>
              )}
              <tr>
                <td style={{ color: "#888" }}>Detectado</td>
                <td style={{ fontSize: "11px" }}>
                  {timestamp ? new Date(timestamp).toLocaleString("pt-BR") : "—"}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Popup>
    </Marker>
  );
}

export default function FireMarker({ detection, focused, onClick }) {
  const lat = parseFloat(detection.latitude);
  const lon = parseFloat(detection.longitude);
  if (isNaN(lat) || isNaN(lon)) return null;
  return <MarkerInner detection={detection} focused={focused} onClick={onClick} />;
}
