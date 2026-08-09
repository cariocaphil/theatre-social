import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./auth-provider";
import { DiaryList } from "./diary-list";
import type { DiaryEntry } from "@/lib/diary";

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

function makeProduction(overrides: Partial<DiaryEntry["production"]> = {}) {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    title: "Hamlet",
    slug: "hamlet",
    work_title: null,
    creator_names: null,
    company_name: null,
    director_name: null,
    venue_name: "Schaubuehne",
    city: null,
    country_code: null,
    premiere_date: null,
    closing_date: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function makeEntry(overrides: Partial<DiaryEntry> = {}): DiaryEntry {
  return {
    id: "22222222-2222-2222-2222-222222222222",
    production_id: "11111111-1111-1111-1111-111111111111",
    production: makeProduction(),
    watched_at: "2026-08-08",
    rating: null,
    review: null,
    created_at: "2026-08-08T00:00:00Z",
    updated_at: "2026-08-08T00:00:00Z",
    ...overrides,
  };
}

function stubApi(routes: {
  diaryEntries?: DiaryEntry[];
  extra?: (url: string, init?: RequestInit) => Response | null;
}) {
  const calls: { url: string; method: string; body: unknown }[] = [];

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const body = init?.body ? JSON.parse(init.body as string) : null;
      calls.push({ url, method, body });

      if (routes.extra) {
        const extraResponse = routes.extra(url, init);
        if (extraResponse) return extraResponse;
      }

      if (url.endsWith("/auth/me")) {
        return jsonResponse(authenticatedUser);
      }
      if (url.includes("/api/v1/diary") && method === "GET" && !url.match(/\/diary\/[^/?]+$/)) {
        return jsonResponse({
          items: routes.diaryEntries ?? [],
          total: routes.diaryEntries?.length ?? 0,
          limit: 20,
          offset: 0,
        });
      }
      return jsonResponse({ detail: "Not found" }, 404);
    }),
  );

  return calls;
}

describe("DiaryList", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows an empty state when the user has no diary entries", async () => {
    stubApi({ diaryEntries: [] });

    render(
      <AuthProvider>
        <DiaryList />
      </AuthProvider>,
    );

    expect(await screen.findByText("You haven't logged any productions yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse the production catalogue" })).toHaveAttribute(
      "href",
      "/productions",
    );
  });

  it("prompts an unauthenticated visitor to log in", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ detail: "Not authenticated" }, 401)),
    );

    render(
      <AuthProvider>
        <DiaryList />
      </AuthProvider>,
    );

    expect(
      await screen.findByText("You need to be logged in to view your diary."),
    ).toBeInTheDocument();
  });

  it("renders returned entries with date, rating, review, and a working production link", async () => {
    stubApi({
      diaryEntries: [makeEntry({ rating: 4.5, review: "A remarkable production." })],
    });

    render(
      <AuthProvider>
        <DiaryList />
      </AuthProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Hamlet" })).toBeInTheDocument();
    expect(screen.getByText("Schaubuehne")).toBeInTheDocument();
    expect(screen.getByText("★★★★½")).toBeInTheDocument();
    expect(screen.getByText("A remarkable production.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Hamlet" })).toHaveAttribute(
      "href",
      "/productions/hamlet",
    );
  });

  it("renders multiple entries for the same production independently", async () => {
    stubApi({
      diaryEntries: [
        makeEntry({ id: "entry-1", watched_at: "2026-08-08", review: "Second viewing." }),
        makeEntry({ id: "entry-2", watched_at: "2026-03-14", review: "First viewing." }),
      ],
    });

    render(
      <AuthProvider>
        <DiaryList />
      </AuthProvider>,
    );

    expect(await screen.findByText("Second viewing.")).toBeInTheDocument();
    expect(screen.getByText("First viewing.")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Hamlet" })).toHaveLength(2);
  });

  it("supports editing an entry and reflects the update without a manual reload", async () => {
    const user = userEvent.setup();
    const entry = makeEntry({ review: "Original review." });
    stubApi({
      diaryEntries: [entry],
      extra: (url, init) => {
        if (url.includes(`/api/v1/diary/${entry.id}`) && init?.method === "PATCH") {
          return jsonResponse({ ...entry, review: "Updated review.", rating: 5 });
        }
        return null;
      },
    });

    render(
      <AuthProvider>
        <DiaryList />
      </AuthProvider>,
    );

    await screen.findByText("Original review.");
    await user.click(screen.getByRole("button", { name: "Edit" }));

    const dialog = screen.getByRole("dialog");
    const reviewField = within(dialog).getByLabelText("Review (optional)");
    await user.clear(reviewField);
    await user.type(reviewField, "Updated review.");
    await user.click(within(dialog).getByRole("radio", { name: "5 stars" }));
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    expect(await screen.findByText("Updated review.")).toBeInTheDocument();
    expect(screen.queryByText("Original review.")).not.toBeInTheDocument();
  });

  it("deletes an entry after confirmation, without a manual reload", async () => {
    const user = userEvent.setup();
    const entry = makeEntry();
    stubApi({
      diaryEntries: [entry],
      extra: (url, init) => {
        if (url.includes(`/api/v1/diary/${entry.id}`) && init?.method === "DELETE") {
          return new Response(null, { status: 204 });
        }
        return null;
      },
    });

    render(
      <AuthProvider>
        <DiaryList />
      </AuthProvider>,
    );

    await screen.findByRole("heading", { name: "Hamlet" });
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(screen.getByText("Delete this entry?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm delete" }));

    await waitFor(() =>
      expect(screen.queryByRole("heading", { name: "Hamlet" })).not.toBeInTheDocument(),
    );
  });

  it("cancelling a delete confirmation leaves the entry in place", async () => {
    const user = userEvent.setup();
    stubApi({ diaryEntries: [makeEntry()] });

    render(
      <AuthProvider>
        <DiaryList />
      </AuthProvider>,
    );

    await screen.findByRole("heading", { name: "Hamlet" });
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(screen.getByRole("heading", { name: "Hamlet" })).toBeInTheDocument();
  });
});
