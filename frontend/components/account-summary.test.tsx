import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountSummary } from "./account-summary";
import { AuthProvider } from "./auth-provider";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("AccountSummary", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the current user's account details when authenticated", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          id: "11111111-1111-1111-1111-111111111111",
          username: "alice",
          email: "alice@example.com",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );

    render(
      <AuthProvider>
        <AccountSummary />
      </AuthProvider>,
    );

    expect(await screen.findByText("alice")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
  });

  it("prompts unauthenticated visitors to log in instead of showing account details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Not authenticated" }, 401)),
    );

    render(
      <AuthProvider>
        <AccountSummary />
      </AuthProvider>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You need to be logged in to view this page.",
    );
  });
});
