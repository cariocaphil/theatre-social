export interface HealthResponse {
  status: string;
  database: string;
}

export type HealthResult = { ok: true; data: HealthResponse } | { ok: false; error: string };

function isHealthResponse(value: unknown): value is HealthResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).status === "string" &&
    typeof (value as Record<string, unknown>).database === "string"
  );
}

/**
 * Fetch `/health` from the given API base URL and normalize the outcome
 * into a result that always has a definite `ok: true | false` shape, so
 * callers never need to deal with thrown exceptions.
 */
export async function fetchHealth(baseUrl: string, init?: RequestInit): Promise<HealthResult> {
  let response: Response;

  try {
    response = await fetch(`${baseUrl}/health`, init);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown network error";
    return { ok: false, error: `Could not reach the API: ${message}` };
  }

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as Record<string, unknown>).detail)
        : `Request failed with status ${response.status}`;
    return { ok: false, error: detail };
  }

  if (!isHealthResponse(body)) {
    return { ok: false, error: "Received a malformed response from the health endpoint" };
  }

  return { ok: true, data: body };
}
