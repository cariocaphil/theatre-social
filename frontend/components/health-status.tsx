"use client";

import { useState } from "react";
import { fetchHealth, type HealthResult } from "@/lib/api";

const PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface HealthStatusProps {
  initialResult: HealthResult;
}

export function HealthStatus({ initialResult }: HealthStatusProps) {
  const [result, setResult] = useState<HealthResult>(initialResult);
  const [isChecking, setIsChecking] = useState(false);

  async function handleCheckAgain() {
    setIsChecking(true);
    const next = await fetchHealth(PUBLIC_API_URL, { cache: "no-store" });
    setResult(next);
    setIsChecking(false);
  }

  return (
    <section aria-label="Backend health status" style={{ marginTop: "1.5rem" }}>
      {isChecking ? (
        <p role="status" style={{ color: "var(--muted)" }}>
          Checking backend status…
        </p>
      ) : result.ok ? (
        <div role="status" style={{ color: "var(--success)" }}>
          <p>API: Reachable</p>
          <p>
            Database: {result.data.database === "connected" ? "Connected" : result.data.database}
          </p>
        </div>
      ) : (
        <div role="alert" style={{ color: "var(--error)" }}>
          <p>API: Unreachable</p>
          <p>{result.error}</p>
        </div>
      )}

      <button
        type="button"
        onClick={handleCheckAgain}
        disabled={isChecking}
        style={{ marginTop: "1rem" }}
      >
        Check again
      </button>
    </section>
  );
}
