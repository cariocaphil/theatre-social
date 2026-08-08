import { notFound } from "next/navigation";
import { ProductionDetail } from "@/components/production-detail";
import { fetchProductionBySlug } from "@/lib/productions";

// Server-side requests (this file, running on the Next.js server inside the
// frontend container) reach the backend via the Compose service name.
const INTERNAL_API_URL = process.env.INTERNAL_API_URL ?? "http://backend:8000";

interface ProductionPageProps {
  params: Promise<{ slug: string }>;
}

export default async function ProductionPage({ params }: ProductionPageProps) {
  const { slug } = await params;
  const result = await fetchProductionBySlug(INTERNAL_API_URL, slug, { cache: "no-store" });

  if (!result.ok && result.notFound) {
    notFound();
  }

  return (
    <main>
      {result.ok ? (
        <ProductionDetail production={result.data} />
      ) : (
        <div role="alert" style={{ color: "var(--error)" }}>
          <p>Could not load this production.</p>
          <p>{result.error}</p>
        </div>
      )}
    </main>
  );
}
