import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProductionList } from "./production-list";
import type { ProductionSummary } from "@/lib/productions";

function makeSummary(overrides: Partial<ProductionSummary> = {}): ProductionSummary {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    title: "Example Production",
    slug: "example-production",
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
    ...overrides,
  };
}

describe("ProductionList", () => {
  it("shows an empty state when there are no productions", () => {
    render(
      <ProductionList result={{ ok: true, data: { items: [], total: 0, limit: 20, offset: 0 } }} />,
    );

    expect(screen.getByText("No productions in the catalogue yet.")).toBeInTheDocument();
  });

  it("shows an error state when the API call failed", () => {
    render(
      <ProductionList result={{ ok: false, error: "Could not reach the API: fetch failed" }} />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Could not reach the API: fetch failed")).toBeInTheDocument();
  });

  it("renders available metadata and links to the detail page by slug", () => {
    const production = makeSummary({
      title: "Hamlet",
      slug: "hamlet",
      work_title: "Hamlet",
      creator_names: "William Shakespeare",
      city: "Berlin",
      country_code: "DE",
      premiere_date: "2026-03-10",
      closing_date: "2026-05-18",
    });

    render(
      <ProductionList
        result={{ ok: true, data: { items: [production], total: 1, limit: 20, offset: 0 } }}
      />,
    );

    expect(screen.getByRole("heading", { name: "Hamlet" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Hamlet" })).toHaveAttribute(
      "href",
      "/productions/hamlet",
    );
    expect(screen.getByText("Based on: Hamlet")).toBeInTheDocument();
    expect(screen.getByText("By William Shakespeare")).toBeInTheDocument();
    expect(screen.getByText("Berlin, DE")).toBeInTheDocument();
    expect(screen.getByText("2026-03-10 – 2026-05-18")).toBeInTheDocument();
  });

  it("does not render labels for missing optional fields", () => {
    const production = makeSummary({ title: "Impro Night Berlin", slug: "impro-night-berlin" });

    render(
      <ProductionList
        result={{ ok: true, data: { items: [production], total: 1, limit: 20, offset: 0 } }}
      />,
    );

    expect(screen.queryByText(/Based on:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^By /)).not.toBeInTheDocument();
  });
});
