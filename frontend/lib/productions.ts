export interface ProductionSummary {
  id: string;
  title: string;
  slug: string;
  work_title: string | null;
  creator_names: string | null;
  company_name: string | null;
  director_name: string | null;
  venue_name: string | null;
  city: string | null;
  country_code: string | null;
  premiere_date: string | null;
  closing_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductionDetail extends ProductionSummary {
  description: string | null;
}

export interface PaginatedProductions {
  items: ProductionSummary[];
  total: number;
  limit: number;
  offset: number;
}

export type ProductionsListResult =
  { ok: true; data: PaginatedProductions } | { ok: false; error: string };

export type ProductionDetailResult =
  | { ok: true; data: ProductionDetail }
  | { ok: false; notFound: true }
  | { ok: false; notFound: false; error: string };

function isPaginatedProductions(value: unknown): value is PaginatedProductions {
  return (
    typeof value === "object" &&
    value !== null &&
    Array.isArray((value as Record<string, unknown>).items) &&
    typeof (value as Record<string, unknown>).total === "number"
  );
}

function isProductionDetail(value: unknown): value is ProductionDetail {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).id === "string" &&
    typeof (value as Record<string, unknown>).title === "string" &&
    typeof (value as Record<string, unknown>).slug === "string"
  );
}

function describeFetchError(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown network error";
}

/**
 * Fetch a page of the Production catalogue. Follows the same
 * always-resolves-to-`{ok, ...}` pattern as `fetchHealth` in `lib/api.ts`
 * so callers never need to deal with thrown exceptions.
 */
export async function fetchProductions(
  baseUrl: string,
  init?: RequestInit,
): Promise<ProductionsListResult> {
  let response: Response;

  try {
    response = await fetch(`${baseUrl}/api/v1/productions`, init);
  } catch (error) {
    return { ok: false, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as Record<string, unknown>).detail)
        : `Request failed with status ${response.status}`;
    return { ok: false, error: detail };
  }

  if (!isPaginatedProductions(body)) {
    return { ok: false, error: "Received a malformed response from the productions endpoint" };
  }

  return { ok: true, data: body };
}

export async function fetchProductionBySlug(
  baseUrl: string,
  slug: string,
  init?: RequestInit,
): Promise<ProductionDetailResult> {
  let response: Response;

  try {
    response = await fetch(`${baseUrl}/api/v1/productions/slug/${encodeURIComponent(slug)}`, init);
  } catch (error) {
    return {
      ok: false,
      notFound: false,
      error: `Could not reach the API: ${describeFetchError(error)}`,
    };
  }

  if (response.status === 404) {
    return { ok: false, notFound: true };
  }

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as Record<string, unknown>).detail)
        : `Request failed with status ${response.status}`;
    return { ok: false, notFound: false, error: detail };
  }

  if (!isProductionDetail(body)) {
    return {
      ok: false,
      notFound: false,
      error: "Received a malformed response from the production endpoint",
    };
  }

  return { ok: true, data: body };
}
