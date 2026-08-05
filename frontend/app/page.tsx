import { HealthStatus } from "@/components/health-status";
import { fetchHealth } from "@/lib/api";

// Server-side requests (this file, running on the Next.js server inside the
// frontend container) reach the backend via the Compose service name.
const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://backend:8000";

export default async function HomePage() {
  const initialResult = await fetchHealth(INTERNAL_API_URL, { cache: "no-store" });

  return (
    <main>
      <h1>Theatre Social</h1>
      <p style={{ color: "var(--muted)", marginTop: "0.5rem" }}>
        Monorepo foundation: Next.js frontend + FastAPI backend + PostgreSQL.
      </p>
      <HealthStatus initialResult={initialResult} />
    </main>
  );
}
