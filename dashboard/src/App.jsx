import React, { useCallback, useEffect, useRef, useState } from "react";
import AlertPanel from "./components/AlertPanel/AlertPanel.jsx";
import FireMap from "./components/Map/FireMap.jsx";
import Header from "./components/Header/Header.jsx";
import { fetchAlerts, fetchDetections, fetchStats } from "./services/api.js";

const POLL_MS = 15 * 60 * 1000;

export default function App() {
  const [detections, setDetections]   = useState([]);
  const [alerts, setAlerts]           = useState([]);
  const [stats, setStats]             = useState({});
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError]             = useState(null);
  const intervalRef                   = useRef(null);

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

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "#0f0f0f", color: "#f0f0f0" }}>
      <Header lastUpdated={lastUpdated} stats={stats} />

      {error && (
        <div style={{
          padding: "6px 16px", background: "#1a0d0d", color: "#ff6b6b",
          fontSize: "11px", borderBottom: "1px solid #2a1a1a",
        }}>
          ⚠ API indisponível: {error}
        </div>
      )}

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        <FireMap detections={detections} onMarkerClick={() => {}} />
        <AlertPanel
          stats={stats}
          alerts={alerts}
          detections={detections}
          onAlertClick={() => {}}
        />
      </div>
    </div>
  );
}
