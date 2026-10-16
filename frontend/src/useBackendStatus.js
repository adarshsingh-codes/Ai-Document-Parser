import { useEffect, useState } from "react";

const CHECK_INTERVAL_MS = 20000;
const TIMEOUT_MS = 5000;

/**
 * Polls the FastAPI backend's own health check (GET /, proxied at /api/)
 * to report real connectivity — not a guess based on the last analyze call.
 */
export function useBackendStatus() {
  const [status, setStatus] = useState("checking"); // "checking" | "online" | "offline"

  useEffect(() => {
    let cancelled = false;

    async function check() {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
      try {
        const res = await fetch("/api/", { signal: controller.signal, cache: "no-store" });
        if (!cancelled) setStatus(res.ok ? "online" : "offline");
      } catch {
        if (!cancelled) setStatus("offline");
      } finally {
        clearTimeout(timeout);
      }
    }

    check();
    const interval = setInterval(check, CHECK_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return status;
}
