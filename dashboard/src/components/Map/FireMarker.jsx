import { divIcon } from "leaflet";
import React from "react";
import { Marker, Popup } from "react-leaflet";

const SEV_COLOR  = { ALTA: "#f44336", MEDIA: "#ff9800", BAIXA: "#4caf50" };
const CLS_EMOJI  = { foco_ativo: "🔥", fumaca: "💨", area_queimada: "🟫" };
const CLS_LABEL  = { foco_ativo: "Foco Ativo", fumaca: "Fumaça", area_queimada: "Área Queimada" };
const BIOMA_ICON = { "Amazônia": "🌳", "Cerrado": "🌿", "Pantanal": "🐊", "Caatinga": "🌵", "Mata Atlântica": "🌲", "Pampa": "🌾" };

function classifyConf(conf) {
  const c = parseFloat(conf);
  if (c >= 0.92) return { label: "ALTA", color: SEV_COLOR.ALTA };
  if (c >= 0.85) return { label: "MEDIA", color: SEV_COLOR.MEDIA };
  return { label: "BAIXA", color: SEV_COLOR.BAIXA };
}

function makeIcon(conf, cls) {
  const { color } = classifyConf(conf);
  const size = cls === "foco_ativo" ? 22 : 16;
  const opacity = cls === "area_queimada" ? 0.6 : 0.9;
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="10" fill="${color}" fill-opacity="${opacity}" stroke="white" stroke-width="2"/>
      ${cls === "foco_ativo" ? '<circle cx="12" cy="12" r="4" fill="white" fill-opacity="0.6"/>' : ""}
    </svg>`;
  return divIcon({ html: svg, className: "", iconSize: [size, size], iconAnchor: [size/2, size/2] });
}

function sourceFromKey(imageKey) {
  if (!imageKey) return "—";
  if (imageKey.includes("modis")) return "MODIS Terra (NASA GIBS)";
  if (imageKey.includes("sentinel2")) return "Sentinel-2 (Copernicus)";
  if (imageKey.includes("nasa_firms")) return "NASA FIRMS";
  if (imageKey.includes("inpe")) return "IBAMA / SISFOGO";
  return "Satélite";
}

export default function FireMarker({ detection, onClick }) {
  const { latitude, longitude, class_name, confidence, timestamp, state, bioma, image_key } = detection;
  const lat = parseFloat(latitude);
  const lon = parseFloat(longitude);
  if (isNaN(lat) || isNaN(lon)) return null;

  const conf  = parseFloat(confidence) || 0;
  const sev   = classifyConf(conf);
  const fonte = sourceFromKey(image_key);
  const biomaIcon = BIOMA_ICON[bioma] || "🌿";

  return (
    <Marker
      position={[lat, lon]}
      icon={makeIcon(confidence, class_name)}
      eventHandlers={{ click: () => onClick?.(detection) }}
    >
      <Popup maxWidth={260}>
        <div style={{ minWidth: "220px", fontFamily: "system-ui, sans-serif", fontSize: "12px", lineHeight: "1.6" }}>

          {/* Título */}
          <div style={{ fontWeight: 700, fontSize: "14px", color: sev.color, marginBottom: "6px" }}>
            {CLS_EMOJI[class_name]} {CLS_LABEL[class_name] ?? class_name}
          </div>

          {/* Métricas YOLO */}
          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "6px" }}>
            <tbody>
              <tr>
                <td style={{ color: "#888", paddingRight: "8px" }}>Confiança</td>
                <td style={{ fontWeight: 700, color: sev.color }}>{(conf * 100).toFixed(1)}%</td>
              </tr>
              <tr>
                <td style={{ color: "#888" }}>Severidade</td>
                <td style={{ fontWeight: 700, color: sev.color }}>{sev.label}</td>
              </tr>
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

          {/* Localização */}
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
              <tr>
                <td style={{ color: "#888" }}>Detectado</td>
                <td style={{ fontSize: "11px" }}>{timestamp ? new Date(timestamp).toLocaleString("pt-BR") : "—"}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Popup>
    </Marker>
  );
}
