import React, { useEffect } from "react";
import { MapContainer, TileLayer, ZoomControl, useMap } from "react-leaflet";
import FireMarker from "./FireMarker.jsx";

const BRAZIL_CENTER = [-14.235, -51.925];
const DEFAULT_ZOOM  = 4;

// Inner component — must be a child of MapContainer to use useMap()
function MapController({ focusedDetection }) {
  const map = useMap();

  useEffect(() => {
    if (!focusedDetection) return;
    const lat = parseFloat(focusedDetection.latitude);
    const lon = parseFloat(focusedDetection.longitude);
    if (!isNaN(lat) && !isNaN(lon)) {
      map.flyTo([lat, lon], 10, { animate: true, duration: 1.2 });
    }
  }, [focusedDetection, map]);

  return null;
}

export default function FireMap({ detections = [], focusedDetection, onMarkerClick }) {
  return (
    <div style={{ flex: 1, position: "relative" }}>
      <MapContainer
        center={BRAZIL_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: "100%", width: "100%", background: "#0f0f0f" }}
        zoomControl={false}
      >
        <ZoomControl position="bottomright" />
        <MapController focusedDetection={focusedDetection} />

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
            focused={focusedDetection?.detection_id === det.detection_id}
            onClick={onMarkerClick}
          />
        ))}
      </MapContainer>
    </div>
  );
}
