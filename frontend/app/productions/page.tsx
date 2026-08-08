import { ProductionList } from "@/components/production-list";
import { fetchProductions } from "@/lib/productions";

// Server-side requests (this file, running on the Next.js server inside the
// frontend container) reach the backend via the Compose service name.
const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://backend:8000";

export default async function ProductionsPage() {
  const result = await fetchProductions(INTERNAL_API_URL, { cache: "no-store" });

  return (
    <main>
      <h1>Productions</h1>
      <p style={{ color: "var(--muted)", marginTop: "0.5rem" }}>
        Browse the theatre-social production catalogue.
      </p>
      <ProductionList result={result} />
    </main>
  );
}
