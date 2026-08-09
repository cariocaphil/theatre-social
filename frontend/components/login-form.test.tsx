import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import { AuthProvider } from "./auth-provider";
import { LoginForm } from "./login-form";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("LoginForm", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    pushMock.mockClear();
  });

  it("renders email, password, and a submit button", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Not authenticated" }, 401)),
    );

    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );

    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log in" })).toBeInTheDocument();
  });

  it("shows a validation error when submitted empty", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Not authenticated" }, 401)),
    );

    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Email and password are required.");
  });

  it("renders the API's generic authentication-failure error", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/auth/login")) {
          return jsonResponse({ detail: "Invalid email or password" }, 401);
        }
        return jsonResponse({ detail: "Not authenticated" }, 401);
      }),
    );

    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");
  });

  it("updates auth state and navigates home after a successful login", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/auth/login")) {
          return jsonResponse({
            id: "11111111-1111-1111-1111-111111111111",
            username: "alice",
            email: "alice@example.com",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          });
        }
        return jsonResponse({ detail: "Not authenticated" }, 401);
      }),
    );

    render(
      <AuthProvider>
        <LoginForm />
      </AuthProvider>,
    );

    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/"));
  });
});
