import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LogDialog } from "./log-dialog";
import type { DiaryEntry } from "@/lib/diary";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function makeEntry(overrides: Partial<DiaryEntry> = {}): DiaryEntry {
  return {
    id: "22222222-2222-2222-2222-222222222222",
    production_id: "11111111-1111-1111-1111-111111111111",
    production: {
      id: "11111111-1111-1111-1111-111111111111",
      title: "Hamlet",
      slug: "hamlet",
      work_title: null,
      creator_names: null,
      company_name: null,
      director_name: null,
      venue_name: null,
      city: null,
      country_code: null,
      premiere_date: null,
      closing_date: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
    watched_at: "2026-08-08",
    rating: null,
    review: null,
    created_at: "2026-08-08T00:00:00Z",
    updated_at: "2026-08-08T00:00:00Z",
    ...overrides,
  };
}

describe("LogDialog", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("identifies the production and defaults the date to today", () => {
    render(
      <LogDialog
        productionId="11111111-1111-1111-1111-111111111111"
        productionTitle="Hamlet"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Log this production" })).toBeInTheDocument();
    expect(screen.getByText("Hamlet")).toBeInTheDocument();

    const dateInput = screen.getByLabelText("Date attended") as HTMLInputElement;
    const today = new Date().toISOString().slice(0, 10);
    expect(dateInput.value).toBe(today);
  });

  it("allows saving with only a production and date (rating/review optional)", async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(makeEntry())),
    );

    render(
      <LogDialog
        productionId="11111111-1111-1111-1111-111111111111"
        productionTitle="Hamlet"
        onClose={vi.fn()}
        onSaved={onSaved}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onSaved).toHaveBeenCalled());
  });

  it("supports selecting a half-star rating and clearing it", async () => {
    const user = userEvent.setup();

    render(
      <LogDialog
        productionId="11111111-1111-1111-1111-111111111111"
        productionTitle="Hamlet"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    expect(screen.getByText("No rating")).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: "4.5 stars" }));
    expect(screen.getByText("4.5 / 5")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear rating" }));
    expect(screen.getByText("No rating")).toBeInTheDocument();
  });

  it("submits an entry with rating and review", async () => {
    const user = userEvent.setup();
    let capturedBody: Record<string, unknown> | null = null;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_url: string, init?: RequestInit) => {
        capturedBody = init?.body ? JSON.parse(init.body as string) : null;
        return jsonResponse(makeEntry({ rating: 4.5, review: "A remarkable production." }));
      }),
    );

    render(
      <LogDialog
        productionId="11111111-1111-1111-1111-111111111111"
        productionTitle="Hamlet"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("radio", { name: "4.5 stars" }));
    await user.type(screen.getByLabelText("Review (optional)"), "A remarkable production.");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(capturedBody).not.toBeNull());
    expect(capturedBody).toMatchObject({ rating: 4.5, review: "A remarkable production." });
  });

  it("prevents duplicate submission while a request is pending", async () => {
    const user = userEvent.setup();
    let resolveFetch: (() => void) | undefined;
    const fetchMock = vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = () => resolve(jsonResponse(makeEntry()));
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <LogDialog
        productionId="11111111-1111-1111-1111-111111111111"
        productionTitle="Hamlet"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    const saveButton = screen.getByRole("button", { name: "Save" });
    await user.click(saveButton);
    await user.click(saveButton);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    resolveFetch?.();
  });

  it("renders an API validation error instead of closing", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Production not found" }, 404)),
    );

    render(
      <LogDialog
        productionId="11111111-1111-1111-1111-111111111111"
        productionTitle="Hamlet"
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Production not found");
  });

  it("pre-fills the form and calls update when editing an existing entry", async () => {
    const user = userEvent.setup();
    const existing = makeEntry({ watched_at: "2026-03-14", rating: 3, review: "First time." });
    let capturedUrl = "";
    let capturedMethod = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        capturedUrl = url;
        capturedMethod = init?.method ?? "GET";
        return jsonResponse({ ...existing, rating: 5, review: "Even better!" });
      }),
    );

    render(
      <LogDialog
        productionId={existing.production_id}
        productionTitle="Hamlet"
        entry={existing}
        onClose={vi.fn()}
        onSaved={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Edit log" })).toBeInTheDocument();
    expect((screen.getByLabelText("Date attended") as HTMLInputElement).value).toBe("2026-03-14");
    expect(screen.getByDisplayValue("First time.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(capturedMethod).toBe("PATCH"));
    expect(capturedUrl).toContain(existing.id);
  });
});
