import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AlertPanel from "./components/AlertPanel/AlertPanel.jsx";
import FireMap from "./components/Map/FireMap.jsx";
import Header from "./components/Header/Header.jsx";
import { fetchAlerts, fetchDetections, fetchStats } from "./services/api.js";

const POLL_MS = 15 * 60 * 1000;

function getSeverity(d) {
  if (d.severity) return d.severity;
  const c = parseFloat(d.confidence) || 0;
  if (c >= 0.92) return "ALTA";
  if (c >= 0.85) return "MEDIA";
  return "BAIXA";
}

function matchesSource(d, source) {
  if (!source) return true;
  const key   = (d.image_key || "").toLowerCase();
  const fonte = (d.fonte     || "").toLowerCase();
  if (source === "firms")    return key.includes("firms")    || fonte.includes("firms");
  if (source === "modis")    return key.includes("modis");
  if (source === "sentinel") return key.includes("sentinel");
  if (source === "inpe")     return key.includes("inpe")     || fonte.includes("ibama");
  return true;
}

export default function App() {
  const [detections, setDetections]           = useState([]);
  const [alerts, setAlerts]                   = useState([]);
  const [stats, setStats]                     = useState({});
  const [lastUpdated, setLastUpdated]         = useState(null);
  const [error, setError]                     = useState(null);
  const [focusedDetection, setFocusedDetection] = useState(null);
  const [activeFilters, setActiveFilters]     = useState({ source: null, class: null, severity: null });
  const intervalRef                           = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [dets, alts, sts] = await Promise.all([
        fetchDetections({ hours: 72, limit: 200 }),
        fetchAlerts(50),
        fetchStats(),
      ]);
      setDetections(dets);
      setAlerts(alts);
      setStats(sts);
      setLastUpdated(new Date().toLocaleTimeString("pt-BR"));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    intervalRef.current = setInterval(refresh, POLL_MS);
    return () => clearInterval(intervalRef.current);
  }, [refresh]);

  const filteredDetections = useMemo(() => {
    return detections.filter(d => {
      if (!matchesSource(d, activeFilters.source)) return false;
      if (activeFilters.class && d.class_name !== activeFilters.class) return false;
      if (activeFilters.severity && getSeverity(d) !== activeFilters.severity) return false;
      return true;
    });
  }, [detections, activeFilters]);

  const uniqueStates = useMemo(() => {
    const states = filteredDetections
      .map(d => d.state)
      .filter(s => s && s !== "BR" && s !== "UNKNOWN");
    return [...new Set(states)];
  }, [filteredDetections]);

  function toggleFilter(key, value) {
    setActiveFilters(prev => ({
      ...prev,
      [key]: prev[key] === value ? null : value,
    }));
  }

  function handleFocusDetection(det) {
    setFocusedDetection(prev =>
      prev?.detection_id === det.detection_id ? null : det
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0f0f0f", color: "#f0f0f0" }}>
      <Header
        lastUpdated={lastUpdated}
        stats={stats}
        uniqueStatesCount={uniqueStates.length}
        activeFilters={activeFilters}
        onFilterChange={toggleFilter}
      />

      {error && (
        <div style={{
          padding: "6px 16px", background: "#1a0d0d", color: "#ff6b6b",
          fontSize: "11px", borderBottom: "1px solid #2a1a1a",
        }}>
          ⚠ API indisponível: {error}
        </div>
      )}

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <FireMap
          detections={filteredDetections}
          focusedDetection={focusedDetection}
          onMarkerClick={handleFocusDetection}
        />
        <AlertPanel
          stats={stats}
          alerts={alerts}
          detections={filteredDetections}
          uniqueStatesCount={uniqueStates.length}
          focusedDetection={focusedDetection}
          onFocusDetection={handleFocusDetection}
          activeFilters={activeFilters}
          onFilterChange={toggleFilter}
          lastUpdated={lastUpdated}
        />
      </div>
    </div>
  );
}
