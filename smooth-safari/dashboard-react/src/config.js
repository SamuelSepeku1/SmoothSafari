// Where liveserver.py is running
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Fallback only. Once the route loads, the map uses the intersection coordinates
// from SSproject/site_config.py, so the marker and the routes can never disagree.
// Still, put the same values here so the map looks right before the route arrives.
export const INTERSECTION = {
  lat: -6.7924,
  lng: 39.2083,
  name: "Monitored intersection",
};
