import React from "react";

export default function StatusBanner({ data, online }) {
  if (!online) {
    return <div className="status warn">Backend offline. Start liveserver.py on port 8000.</div>;
  }
  if (data?.status === "error") {
    return <div className="status bad">{data.message}</div>;
  }
  if (data?.status !== "running") {
    return <div className="status warn">Loading the detection model…</div>;
  }
  if (data.congested) {
    return (
      <div className="status bad">
        <strong>Congestion detected</strong> ({data.total_vehicles} vehicles queued). Reroute
        suggested for approaching traffic.
      </div>
    );
  }
  return (
    <div className="status ok">
      <strong>Traffic flowing normally</strong> ({data.total_vehicles} vehicles queued)
    </div>
  );
}
