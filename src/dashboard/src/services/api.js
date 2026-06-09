// Em dev o Vite proxy encaminha /api → VITE_API_BASE_URL (sem CORS).
// Em prod (build) usa a URL completa do API Gateway.
const BASE_URL = import.meta.env.DEV
  ? "/api"
  : (import.meta.env.VITE_API_BASE_URL || "/api");

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

/**
 * Fetch recent fire detections.
 * @param {Object} params
 * @param {string} [params.state]      - Filter by Brazilian state code e.g. "AM"
 * @param {number} [params.hours=24]   - Look-back window in hours
 * @param {number} [params.limit=200]  - Max records
 */
export async function fetchDetections({ state, hours = 72, limit = 200 } = {}) {
  const qs = new URLSearchParams({ hours, limit });
  if (state) qs.set("state", state);
  const data = await request(`/detections?${qs}`);
  return data.detections ?? data;
}


/**
 * Fetch dashboard summary statistics.
 * @returns {{ total_focos: number, area_ha: number, top_state: string, last_updated: string }}
 */
export async function fetchStats() {
  return request("/stats");
}

/**
 * Fetch the most recent alerts (for the AlertPanel).
 * @param {number} limit
 */
export async function fetchAlerts(limit = 20) {
  const data = await request(`/alerts?limit=${limit}`);
  return data.alerts ?? data;
}
