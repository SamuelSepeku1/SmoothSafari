import React from "react";
import { useLatest } from "./hooks/useLatest";
import VideoFeed from "./components/VideoFeed";
import LanePanel from "./components/LanePanel";
import StatusBanner from "./components/StatusBanner";
import MapView from "./components/MapView";


export default function App() {
  const { data, online } = useLatest(500);

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Smooth Safari</h1>
          <p>Two-tier computer vision + ML traffic control · Dar es Salaam</p>
        </div>
      </header>

      <main className="grid">
        <div className="col">
          <VideoFeed online={online} fps={data?.fps} />
          <MapView congested={data?.congested} />
        </div>
        <div className="col side">
          <StatusBanner data={data} online={online} />
          <LanePanel data={data} />
        </div>
      </main>
    </div>
  );
}
