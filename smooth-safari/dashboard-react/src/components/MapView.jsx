import React, { useEffect, useState } from "react";
import { MapContainer,TileLayer,CircleMarker,Popup,Polyline,Tooltip,useMap } from "react-leaflet";
import { INTERSECTION as FALLBACK, API_URL } from "../config";

// Zooms the map so the whole route is visible whenever the route changes
function FitToRoute({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 1) map.fitBounds(points, { padding: [30, 30] });
  }, [points, map]);
  return null;
}

export default function MapView({ congested }) {
  const isCongested = Boolean(congested);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);

  // Ask the backend for the Dijkstra route that matches the live congestion state.
  // If the server is not reachable yet (still starting, restarted, wrong port), keep
  // retrying every 4 seconds so the map recovers on its own.
  useEffect(() => {
    let cancelled = false;
    let timer = null;

    const load = () => {
      fetch(`${API_URL}/api/route?congested=${isCongested}`)
        .then((res) => {
          if (!res.ok) throw new Error(`server answered HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          if (cancelled) return;
          if (data.error) {
            setError(data.error); // a real problem (for example the saved map); retrying will not fix it
            setInfo(null);
          } else {
            setError(null);
            setInfo(data);
          }
        })
        .catch((e) => {
          if (cancelled) return;
          const unreachable = e instanceof TypeError;
          setError(
            unreachable
              ? `cannot reach the server at ${API_URL} (retrying...)`
              : `${e.message} (retrying...)`
          );
          timer = setTimeout(load, 4000);
        });
    };

    load();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [isCongested]);

  const place = info?.intersection ?? FALLBACK;
  const position = [place.lat, place.lng];
  const route = (info?.route ?? []).map((p) => [p.lat, p.lng]);
  const color = isCongested ? "#ff5c5c" : "#3ddc84";
  const routeColor = isCongested ? "#ff5c5c" : "#3b82f6";

  return (
    <section className="card">
      <div className="card-head">
        <h2>Route through the junction</h2>
        <span className="muted">Dijkstra · OpenStreetMap</span>
      </div>

      <MapContainer center={position} zoom={16} scrollWheelZoom={false} className="map">
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitToRoute points={route} />

        {/* ONE route at a time:
            not congested -> blue route THROUGH the intersection
            congested     -> red route AROUND the intersection */}
        {route.length > 0 && (
          <Polyline positions={route} pathOptions={{ color: routeColor, weight: 6 }} />
        )}

        {info?.origin && (
          <CircleMarker
            center={[info.origin.lat, info.origin.lng]}
            radius={7}
            pathOptions={{ color: "#111", fillColor: "#fff", fillOpacity: 1 }}
          >
            <Tooltip permanent direction="top">A</Tooltip>
          </CircleMarker>
        )}
        {info?.destination && (
          <CircleMarker
            center={[info.destination.lat, info.destination.lng]}
            radius={7}
            pathOptions={{ color: "#111", fillColor: "#fff", fillOpacity: 1 }}
          >
            <Tooltip permanent direction="top">B</Tooltip>
          </CircleMarker>
        )}

        <CircleMarker
          center={position}
          radius={14}
          pathOptions={{ color, fillColor: color, fillOpacity: 0.5 }}
        >
          <Popup>{place.name}</Popup>
        </CircleMarker>
      </MapContainer>

      <p className="muted" style={{ marginTop: "8px" }}>
        {error
          ? `Route unavailable: ${error}`
          : !info
          ? "Loading route..."
          : isCongested
          ? `Junction congested: Dijkstra found a path around the intersection (${info.length_m} m, at least ${info.closest_approach_m} m away from it).`
          : `Traffic flowing: the shortest path goes through the intersection (${info.length_m} m).`}
      </p>
    </section>
  );
}