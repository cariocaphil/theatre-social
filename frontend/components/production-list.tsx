import Link from "next/link";
import type { ProductionsListResult, ProductionSummary } from "@/lib/productions";

interface ProductionListProps {
  result: ProductionsListResult;
}

function formatLocation(city: string | null, countryCode: string | null): string | null {
  if (city && countryCode) return `${city}, ${countryCode}`;
  if (city) return city;
  if (countryCode) return countryCode;
  return null;
}

function formatDates(premiereDate: string | null, closingDate: string | null): string | null {
  if (premiereDate && closingDate) return `${premiereDate} – ${closingDate}`;
  if (premiereDate) return `From ${premiereDate}`;
  if (closingDate) return `Until ${closingDate}`;
  return null;
}

function ProductionListItem({ production }: { production: ProductionSummary }) {
  const location = formatLocation(production.city, production.country_code);
  const dates = formatDates(production.premiere_date, production.closing_date);

  return (
    <li style={{ borderBottom: "1px solid var(--border)", padding: "1.25rem 0" }}>
      <Link href={`/productions/${production.slug}`}>
        <h2 style={{ fontSize: "1.15rem" }}>{production.title}</h2>
      </Link>
      {production.work_title && (
        <p style={{ color: "var(--muted)" }}>Based on: {production.work_title}</p>
      )}
      {production.creator_names && <p>By {production.creator_names}</p>}
      {production.company_name && <p>{production.company_name}</p>}
      {production.director_name && <p>Directed by {production.director_name}</p>}
      {production.venue_name && <p>{production.venue_name}</p>}
      {location && <p style={{ color: "var(--muted)" }}>{location}</p>}
      {dates && <p style={{ color: "var(--muted)" }}>{dates}</p>}
    </li>
  );
}

export function ProductionList({ result }: ProductionListProps) {
  if (!result.ok) {
    return (
      <div role="alert" style={{ color: "var(--error)", marginTop: "1.5rem" }}>
        <p>Could not load productions.</p>
        <p>{result.error}</p>
      </div>
    );
  }

  if (result.data.items.length === 0) {
    return (
      <p style={{ marginTop: "1.5rem", color: "var(--muted)" }}>
        No productions in the catalogue yet.
      </p>
    );
  }

  return (
    <ul style={{ listStyle: "none", marginTop: "1.5rem" }}>
      {result.data.items.map((production) => (
        <ProductionListItem key={production.id} production={production} />
      ))}
    </ul>
  );
}
