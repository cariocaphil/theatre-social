import { LogProductionAction } from "@/components/log-production-action";
import type { ProductionDetail as ProductionDetailData } from "@/lib/productions";

interface ProductionDetailProps {
  production: ProductionDetailData;
}

function formatLocation(city: string | null, countryCode: string | null): string | null {
  if (city && countryCode) return `${city}, ${countryCode}`;
  if (city) return city;
  if (countryCode) return countryCode;
  return null;
}

export function ProductionDetail({ production }: ProductionDetailProps) {
  const location = formatLocation(production.city, production.country_code);

  return (
    <article>
      <h1>{production.title}</h1>

      <div style={{ marginTop: "1rem" }}>
        <LogProductionAction productionId={production.id} productionTitle={production.title} />
      </div>

      {production.description && <p style={{ marginTop: "1rem" }}>{production.description}</p>}

      <dl style={{ marginTop: "1.5rem" }}>
        {production.work_title && (
          <div style={{ marginBottom: "0.75rem" }}>
            <dt style={{ color: "var(--muted)" }}>Based on</dt>
            <dd>{production.work_title}</dd>
          </div>
        )}
        {production.creator_names && (
          <div style={{ marginBottom: "0.75rem" }}>
            <dt style={{ color: "var(--muted)" }}>Creators</dt>
            <dd>{production.creator_names}</dd>
          </div>
        )}
        {production.company_name && (
          <div style={{ marginBottom: "0.75rem" }}>
            <dt style={{ color: "var(--muted)" }}>Company</dt>
            <dd>{production.company_name}</dd>
          </div>
        )}
        {production.director_name && (
          <div style={{ marginBottom: "0.75rem" }}>
            <dt style={{ color: "var(--muted)" }}>Director</dt>
            <dd>{production.director_name}</dd>
          </div>
        )}
        {production.venue_name && (
          <div style={{ marginBottom: "0.75rem" }}>
            <dt style={{ color: "var(--muted)" }}>Venue</dt>
            <dd>{production.venue_name}</dd>
          </div>
        )}
        {location && (
          <div style={{ marginBottom: "0.75rem" }}>
            <dt style={{ color: "var(--muted)" }}>Location</dt>
            <dd>{location}</dd>
          </div>
        )}
        {production.premiere_date && (
          <div style={{ marginBottom: "0.75rem" }}>
            <dt style={{ color: "var(--muted)" }}>Premiere</dt>
            <dd>{production.premiere_date}</dd>
          </div>
        )}
        {production.closing_date && (
          <div style={{ marginBottom: "0.75rem" }}>
            <dt style={{ color: "var(--muted)" }}>Closing</dt>
            <dd>{production.closing_date}</dd>
          </div>
        )}
      </dl>
    </article>
  );
}
