import React from "react";

export default function LanePanel({ data }) {
  if (!data?.green_time_seconds) {
    return (
      <section className="card">
        <div className="card-head">
          <h2>Adaptive signal plan</h2>
        </div>
        <p className="muted">Waiting for data…</p>
      </section>
    );
  }

  const maxGreen = data.max_green_seconds ?? 35;

  return (
    <section className="card">
      <div className="card-head">
        <h2>Adaptive signal plan</h2>
        <span className="muted">green time per cycle</span>
      </div>

      {Object.entries(data.green_time_seconds).map(([lane, green]) => {
        const priority = lane === data.priority_lane;
        const live = data.live_counts?.[lane] ?? 0;
        const avg = data.avg_queue_counts?.[lane] ?? 0;

        return (
          <div key={lane} className={`lane ${priority ? "priority" : ""}`}>
            <div className="lane-top">
              <span className="lane-name">
                {lane.replace("_", " ")}
                {priority && <span className="star">★ priority</span>}
              </span>
              <span className="lane-live">
                <strong>{live}</strong> vehicles now
              </span>
            </div>
            <div className="bar">
              <div
                className="bar-fill"
                style={{ width: `${Math.min(100, (green / maxGreen) * 100)}%` }}
              />
            </div>
            <div className="lane-meta">
              <span>{green}s green</span>
              <span>{avg.toFixed(1)} avg queue</span>
            </div>
          </div>
        );
      })}
    </section>
  );
}
