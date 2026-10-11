import React, { useEffect, useState } from "react";
import { API_URL } from "../config";

export default function VideoFeed({ online, fps }) {
  const [attempt, setAttempt] = useState(0);
  const [failed, setFailed] = useState(false);

  // if the stream drops, retry every 3 seconds
  useEffect(() => {
    if (!failed) return;
    const id = setTimeout(() => {
      setFailed(false);
      setAttempt((a) => a + 1);
    }, 3000);
    return () => clearTimeout(id);
  }, [failed]);

  const live = online && !failed;

  return (
    <section className="card">
      <div className="card-head">
        <h2>Live camera analysis</h2>
        <span className={`badge ${live ? "live" : "offline"}`}>
          {live ? "LIVE" : "OFFLINE"}
        </span>
      </div>

      <div className="video-wrap">
        {failed ? (
          <div className="video-placeholder">
            Waiting for the video stream. Is liveserver.py running?
          </div>
        ) : (
          <img
            src={`${API_URL}/video_feed?attempt=${attempt}`}
            alt="Annotated intersection feed"
            onError={() => setFailed(true)}
          />
        )}
      </div>

      {live && fps ? <div className="video-meta">{fps} frames/sec processed on CPU</div> : null}
    </section>
  );
}
