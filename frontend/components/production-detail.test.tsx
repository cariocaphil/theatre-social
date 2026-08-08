import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ProductionDetail } from "./production-detail";
import type { ProductionDetail as ProductionDetailData } from "@/lib/productions";

function makeDetail(overrides: Partial<ProductionDetailData> = {}): ProductionDetailData {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    title: "Example Production",
    slug: "example-production",
    description: null,
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

describe("ProductionDetail", () => {
  it("renders every field when fully populated", () => {
    const production = makeDetail({
      title: "Hamlet",
      description: "A staging of Shakespeare's tragedy.",
      work_title: "Hamlet",
      creator_names: "William Shakespeare",
      company_name: "Example Ensemble",
      director_name: "Sample Director",
      venue_name: "Example Theatre",
      city: "Berlin",
      country_code: "DE",
      premiere_date: "2026-03-10",
      closing_date: "2026-05-18",
    });

    render(<ProductionDetail production={production} />);

    expect(screen.getByRole("heading", { name: "Hamlet" })).toBeInTheDocument();
    expect(screen.getByText("A staging of Shakespeare's tragedy.")).toBeInTheDocument();
    expect(screen.getByText("Hamlet", { selector: "dd" })).toBeInTheDocument();
    expect(screen.getByText("William Shakespeare")).toBeInTheDocument();
    expect(screen.getByText("Example Ensemble")).toBeInTheDocument();
    expect(screen.getByText("Sample Director")).toBeInTheDocument();
    expect(screen.getByText("Example Theatre")).toBeInTheDocument();
    expect(screen.getByText("Berlin, DE")).toBeInTheDocument();
    expect(screen.getByText("2026-03-10")).toBeInTheDocument();
    expect(screen.getByText("2026-05-18")).toBeInTheDocument();
  });

  it("renders correctly with every optional field missing, without empty labels", () => {
    const production = makeDetail({ title: "Impro Night Berlin" });

    render(<ProductionDetail production={production} />);

    expect(screen.getByRole("heading", { name: "Impro Night Berlin" })).toBeInTheDocument();
    expect(screen.queryByText("Based on")).not.toBeInTheDocument();
    expect(screen.queryByText("Creators")).not.toBeInTheDocument();
    expect(screen.queryByText("Company")).not.toBeInTheDocument();
    expect(screen.queryByText("Director")).not.toBeInTheDocument();
    expect(screen.queryByText("Venue")).not.toBeInTheDocument();
    expect(screen.queryByText("Location")).not.toBeInTheDocument();
    expect(screen.queryByText("Premiere")).not.toBeInTheDocument();
    expect(screen.queryByText("Closing")).not.toBeInTheDocument();
  });
});
