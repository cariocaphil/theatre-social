import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth-provider";
import { Nav } from "./nav";

const AUTHENTICATED_USER = {
  id: "11111111-1111-1111-1111-111111111111",
  username: "alice",
  email: "alice@example.com",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Nav", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows Log in / Sign up links when unauthenticated", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Not authenticated" }, 401)),
    );

    render(
      <AuthProvider>
        <Nav />
      </AuthProvider>,
    );

    expect(await screen.findByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign up" })).toBeInTheDocument();
  });

  it("shows a USERNAME menu (with an Account link to /me) when authenticated", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(AUTHENTICATED_USER)),
    );

    render(
      <AuthProvider>
        <Nav />
      </AuthProvider>,
    );

    const menuButton = await screen.findByRole("button", { name: /ALICE/ });
    expect(screen.queryByRole("link", { name: "Log in" })).not.toBeInTheDocument();

    await user.click(menuButton);

    const accountLink = screen.getByRole("menuitem", { name: "Account" });
    expect(accountLink).toHaveAttribute("href", "/me");
    expect(screen.getByRole("menuitem", { name: "Log out" })).toBeInTheDocument();
  });

  it("logging out returns the nav to its unauthenticated state", async () => {
    const user = userEvent.setup();

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/auth/logout")) {
          return new Response(null, { status: 204 });
        }
        return jsonResponse(AUTHENTICATED_USER);
      }),
    );

    render(
      <AuthProvider>
        <Nav />
      </AuthProvider>,
    );

    const menuButton = await screen.findByRole("button", { name: /ALICE/ });
    await user.click(menuButton);
    await user.click(screen.getByRole("menuitem", { name: "Log out" }));

    expect(await screen.findByRole("link", { name: "Log in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign up" })).toBeInTheDocument();
  });
});
