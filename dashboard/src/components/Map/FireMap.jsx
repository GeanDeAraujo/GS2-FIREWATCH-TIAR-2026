import React from "react";
import { MapContainer, TileLayer, ZoomControl } from "react-leaflet";
import FireMarker from "./FireMarker.jsx";

// Brazil center
const BRAZIL_CENTER = [-14.235, -51.925];
const DEFAULT_ZOOM = 4;

const styles = {
  mapWrapper: { flex: 1, position: "relative" },
};

export default function FireMap({ detections = [], onMarkerClick }) {
  return (
    <div style={styles.mapWrapper}>
      <MapContainer
        center={BRAZIL_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: "100%", width: "100%", background: "#0f0f0f" }}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />

        {/* Dark base map */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          subdomains="abcd"
          maxZoom={19}
        />

        {detections.map((det) => (
          <FireMarker
            key={det.detection_id}
            detection={det}
            onClick={onMarkerClick}
          />
        ))}
      </MapContainer>
    </div>
  );
}
