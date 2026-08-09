/**
 * Diary API client, following the same always-resolves-to-`{ok, ...}`
 * pattern as `lib/auth.ts` / `lib/productions.ts`. Every diary endpoint is
 * authenticated via the HTTP-only session cookie, so every request here
 * needs `credentials: "include"`, same as `lib/auth.ts`.
 */

import type { ProductionSummary } from "@/lib/productions";

// Mirrors `MAX_REVIEW_LENGTH` in `backend/app/schemas/diary.py`. The backend
// is authoritative; this is only used for frontend-side UX (character
// counter, `maxLength` on the textarea).
export const MAX_REVIEW_LENGTH = 4000;

export interface DiaryEntry {
  id: string;
  production_id: string;
  production: ProductionSummary;
  watched_at: string;
  rating: number | null;
  review: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedDiaryEntries {
  items: DiaryEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface DiaryEntryCreateInput {
  production_id: string;
  watched_at: string;
  rating?: number | null;
  review?: string | null;
}

export interface DiaryEntryUpdateInput {
  watched_at?: string;
  rating?: number | null;
  review?: string | null;
}

export type DiaryListResult =
  { ok: true; data: PaginatedDiaryEntries } | { ok: false; error: string };

export type DiaryEntryResult =
  { ok: true; data: DiaryEntry } | { ok: false; status: number; error: string };

export type DiaryActionResult = { ok: true } | { ok: false; error: string };

function describeFetchError(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown network error";
}

/**
 * FastAPI's `detail` is either a plain string (`HTTPException`) or a list
 * of Pydantic validation error objects (422 responses). Both are
 * normalized into one human-readable string, same as `lib/auth.ts`.
 */
function extractErrorDetail(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object" || !("detail" in body)) {
    return fallback;
  }

  const detail = (body as Record<string, unknown>).detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) =>
        item && typeof item === "object" && "msg" in item
          ? String((item as Record<string, unknown>).msg)
          : null,
      )
      .filter((msg): msg is string => Boolean(msg));
    if (messages.length > 0) {
      return messages.join("; ");
    }
  }

  return fallback;
}

function isDiaryEntry(value: unknown): value is DiaryEntry {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).id === "string" &&
    typeof (value as Record<string, unknown>).production_id === "string" &&
    typeof (value as Record<string, unknown>).watched_at === "string"
  );
}

function isPaginatedDiaryEntries(value: unknown): value is PaginatedDiaryEntries {
  return (
    typeof value === "object" &&
    value !== null &&
    Array.isArray((value as Record<string, unknown>).items) &&
    typeof (value as Record<string, unknown>).total === "number"
  );
}

export async function fetchDiaryEntries(
  baseUrl: string,
  params?: { limit?: number; offset?: number },
): Promise<DiaryListResult> {
  const query = new URLSearchParams();
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.offset !== undefined) query.set("offset", String(params.offset));
  const suffix = query.toString() ? `?${query.toString()}` : "";

  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/diary${suffix}`, {
      credentials: "include",
      cache: "no-store",
    });
  } catch (error) {
    return { ok: false, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    return {
      ok: false,
      error: extractErrorDetail(body, `Request failed with status ${response.status}`),
    };
  }

  if (!isPaginatedDiaryEntries(body)) {
    return { ok: false, error: "Received a malformed response from the diary endpoint" };
  }

  return { ok: true, data: body };
}

export async function fetchDiaryEntry(baseUrl: string, entryId: string): Promise<DiaryEntryResult> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/diary/${encodeURIComponent(entryId)}`, {
      credentials: "include",
      cache: "no-store",
    });
  } catch (error) {
    return { ok: false, status: 0, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  return parseDiaryEntryResponse(response);
}

export async function createDiaryEntry(
  baseUrl: string,
  payload: DiaryEntryCreateInput,
): Promise<DiaryEntryResult> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/diary`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    return { ok: false, status: 0, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  return parseDiaryEntryResponse(response);
}

export async function updateDiaryEntry(
  baseUrl: string,
  entryId: string,
  payload: DiaryEntryUpdateInput,
): Promise<DiaryEntryResult> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/diary/${encodeURIComponent(entryId)}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    return { ok: false, status: 0, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  return parseDiaryEntryResponse(response);
}

export async function deleteDiaryEntry(
  baseUrl: string,
  entryId: string,
): Promise<DiaryActionResult> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/diary/${encodeURIComponent(entryId)}`, {
      method: "DELETE",
      credentials: "include",
    });
  } catch (error) {
    return { ok: false, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  if (response.status === 204 || response.ok) {
    return { ok: true };
  }

  const body: unknown = await response.json().catch(() => null);
  return {
    ok: false,
    error: extractErrorDetail(body, `Request failed with status ${response.status}`),
  };
}

async function parseDiaryEntryResponse(response: Response): Promise<DiaryEntryResult> {
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      error: extractErrorDetail(body, `Request failed with status ${response.status}`),
    };
  }

  if (!isDiaryEntry(body)) {
    return {
      ok: false,
      status: response.status,
      error: "Received a malformed response from the diary endpoint",
    };
  }

  return { ok: true, data: body };
}
