import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HealthStatus } from "./health-status";

describe("HealthStatus", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("displays a successful API and database status", () => {
    render(
      <HealthStatus initialResult={{ ok: true, data: { status: "ok", database: "connected" } }} />,
    );

    expect(screen.getByText("API: Reachable")).toBeInTheDocument();
    expect(screen.getByText("Database: Connected")).toBeInTheDocument();
  });

  it("displays a clear error state when the backend is unreachable", () => {
    render(
      <HealthStatus
        initialResult={{ ok: false, error: "Could not reach the API: fetch failed" }}
      />,
    );

    expect(screen.getByText("API: Unreachable")).toBeInTheDocument();
    expect(screen.getByText("Could not reach the API: fetch failed")).toBeInTheDocument();
  });

  it("shows a loading state while re-checking, then displays the refreshed result", async () => {
    const user = userEvent.setup();

    let resolveFetch!: (value: Response) => void;
    const fetchPromise = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(() => fetchPromise),
    );

    render(
      <HealthStatus
        initialResult={{ ok: false, error: "Could not reach the API: fetch failed" }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Check again" }));

    expect(screen.getByText("Checking backend status…")).toBeInTheDocument();

    resolveFetch(
      new Response(JSON.stringify({ status: "ok", database: "connected" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await waitFor(() => {
      expect(screen.getByText("API: Reachable")).toBeInTheDocument();
    });
  });
});
