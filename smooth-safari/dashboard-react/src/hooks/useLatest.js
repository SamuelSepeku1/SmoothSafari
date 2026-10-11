import { useEffect, useState } from "react";
import { API_URL } from "../config";

// Polls the backend for the latest counts + signal plan.
export function useLatest(intervalMs = 500) {
  const [data, setData] = useState(null);
  const [online, setOnline] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch(`${API_URL}/api/latest`);
        const json = await res.json();
        if (!cancelled) {
          setData(json);
          setOnline(true);
        }
      } catch {
        if (!cancelled) setOnline(false);
      }
    }

    poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { data, online };
}
