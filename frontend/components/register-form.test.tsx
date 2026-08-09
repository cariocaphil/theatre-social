import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

import { AuthProvider } from "./auth-provider";
import { RegisterForm } from "./register-form";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("RegisterForm", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    pushMock.mockClear();
  });

  it("renders username, email, password, and a submit button", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Not authenticated" }, 401)),
    );

    render(
      <AuthProvider>
        <RegisterForm />
      </AuthProvider>,
    );

    expect(screen.getByLabelText("Username")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign up" })).toBeInTheDocument();
  });

  it("shows a validation error when the password is too short", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Not authenticated" }, 401)),
    );

    render(
      <AuthProvider>
        <RegisterForm />
      </AuthProvider>,
    );

    await user.type(screen.getByLabelText("Username"), "alice");
    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "short");
    await user.click(screen.getByRole("button", { name: "Sign up" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Password must be at least 8 characters.",
    );
  });

  it("renders a duplicate-username/email API error", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/auth/register")) {
          return jsonResponse({ detail: "Username is already taken" }, 409);
        }
        return jsonResponse({ detail: "Not authenticated" }, 401);
      }),
    );

    render(
      <AuthProvider>
        <RegisterForm />
      </AuthProvider>,
    );

    await user.type(screen.getByLabelText("Username"), "taken");
    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Sign up" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Username is already taken");
  });

  it("updates auth state and navigates home after successful registration", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/auth/register")) {
          return jsonResponse(
            {
              id: "11111111-1111-1111-1111-111111111111",
              username: "alice",
              email: "alice@example.com",
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
            },
            201,
          );
        }
        return jsonResponse({ detail: "Not authenticated" }, 401);
      }),
    );

    render(
      <AuthProvider>
        <RegisterForm />
      </AuthProvider>,
    );

    await user.type(screen.getByLabelText("Username"), "alice");
    await user.type(screen.getByLabelText("Email"), "alice@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-password");
    await user.click(screen.getByRole("button", { name: "Sign up" }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/"));
  });
});
