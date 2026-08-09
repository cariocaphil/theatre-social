/**
 * Authentication API client, following the same always-resolves-to-`{ok,
 * ...}` pattern as `lib/api.ts` / `lib/productions.ts`. The backend uses an
 * HTTP-only session cookie (never a token read by JavaScript), so every
 * request here needs `credentials: "include"` for the browser to send/
 * receive it -- this is the only thing that differs from the read-only
 * catalogue client.
 */

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  created_at: string;
  updated_at: string;
}

export type AuthResult =
  | { ok: true; data: AuthUser }
  | { ok: false; status: number; error: string };

export type ActionResult = { ok: true } | { ok: false; error: string };

function isAuthUser(value: unknown): value is AuthUser {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as Record<string, unknown>).id === "string" &&
    typeof (value as Record<string, unknown>).username === "string" &&
    typeof (value as Record<string, unknown>).email === "string"
  );
}

function describeFetchError(error: unknown): string {
  return error instanceof Error ? error.message : "Unknown network error";
}

/**
 * FastAPI's `detail` is either a plain string (`HTTPException`) or a list
 * of Pydantic validation error objects (422 responses). Both are
 * normalized into one human-readable string.
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

async function parseAuthResponse(response: Response): Promise<AuthResult> {
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    return {
      ok: false,
      status: response.status,
      error: extractErrorDetail(body, `Request failed with status ${response.status}`),
    };
  }

  if (!isAuthUser(body)) {
    return {
      ok: false,
      status: response.status,
      error: "Received a malformed response from the auth endpoint",
    };
  }

  return { ok: true, data: body };
}

/**
 * Fetch the current authenticated User, or an `ok: false` result (notably
 * `status: 401` when there is no valid session -- callers should treat
 * that as "signed out", not as an error to display).
 */
export async function fetchCurrentUser(baseUrl: string): Promise<AuthResult> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/me`, {
      credentials: "include",
      cache: "no-store",
    });
  } catch (error) {
    return { ok: false, status: 0, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  return parseAuthResponse(response);
}

export async function registerUser(
  baseUrl: string,
  payload: { username: string; email: string; password: string },
): Promise<AuthResult> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/register`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    return { ok: false, status: 0, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  return parseAuthResponse(response);
}

export async function loginUser(
  baseUrl: string,
  payload: { email: string; password: string },
): Promise<AuthResult> {
  let response: Response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/login`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    return { ok: false, status: 0, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  return parseAuthResponse(response);
}

export async function logoutUser(baseUrl: string): Promise<ActionResult> {
  try {
    await fetch(`${baseUrl}/api/v1/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
  } catch (error) {
    return { ok: false, error: `Could not reach the API: ${describeFetchError(error)}` };
  }

  // Logout is designed to be safe/idempotent server-side, and the browser
  // should always end up "logged out" client-side regardless of the
  // response, so no status/body inspection is needed here.
  return { ok: true };
}
