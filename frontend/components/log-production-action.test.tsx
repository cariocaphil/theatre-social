import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth-provider";
import { LogProductionAction } from "./log-production-action";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const authenticatedUser = {
  id: "33333333-3333-3333-3333-333333333333",
  username: "alice",
  email: "alice@example.com",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("LogProductionAction", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("prompts an unauthenticated visitor to log in, following the existing auth UX", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Not authenticated" }, 401)),
    );

    render(
      <AuthProvider>
        <LogProductionAction productionId="p-1" productionTitle="Hamlet" />
      </AuthProvider>,
    );

    expect(await screen.findByRole("link", { name: "Log in" })).toHaveAttribute("href", "/login");
    expect(screen.queryByRole("button", { name: "Log this production" })).not.toBeInTheDocument();
  });

  it("shows 'Log this production' for authenticated users and opens the dialog", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(authenticatedUser)),
    );

    render(
      <AuthProvider>
        <LogProductionAction productionId="p-1" productionTitle="Hamlet" />
      </AuthProvider>,
    );

    const trigger = await screen.findByRole("button", { name: "Log this production" });
    await user.click(trigger);

    expect(screen.getByRole("heading", { name: "Log this production" })).toBeInTheDocument();
    expect(screen.getAllByText("Hamlet").length).toBeGreaterThan(0);
  });
});
