import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Home from "../../src/pages/Home";

function renderHome() {
  return render(
    <MemoryRouter>
      <Home />
    </MemoryRouter>
  );
}

describe("Home", () => {
  it("renders the main hero content", () => {
    renderHome();

    expect(
      screen.getByText("Mobile-first job matching for early careers")
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /find the roles you can actually grow into/i,
      })
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /earlybloom helps entry-level and junior candidates cut through fake/i
      )
    ).toBeInTheDocument();
  });

  it("renders the primary hero actions with correct routes", () => {
    renderHome();

    const startExploringLink = screen.getByRole("link", {
      name: /start exploring/i,
    });
    const learnMoreLink = screen.getByRole("link", {
      name: /learn more/i,
    });

    expect(startExploringLink).toBeInTheDocument();
    expect(startExploringLink).toHaveAttribute("href", "/jobs");

    expect(learnMoreLink).toBeInTheDocument();
    expect(learnMoreLink).toHaveAttribute("href", "/learn-more");
  });

  it("renders the product highlight tags", () => {
    renderHome();

    const highlights = screen.getByLabelText(/product highlights/i);

    expect(within(highlights).getByText(/real fit scoring/i)).toBeInTheDocument();
    expect(
      within(highlights).getByText(/junior-friendly filtering/i)
    ).toBeInTheDocument();
    expect(
      within(highlights).getByText(/application tracking/i)
    ).toBeInTheDocument();
  });

  it("renders the mascot image with accessible alt text", () => {
    renderHome();

    expect(
      screen.getByRole("img", {
        name: /bloombug mascot holding a small seedling/i,
      })
    ).toBeInTheDocument();
  });

  it("renders the mission section", () => {
    renderHome();

    expect(screen.getByText("Mission")).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        level: 2,
        name: /entry-level should mean entry-level/i,
      })
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /too many job boards flood early-career candidates with listings/i
      )
    ).toBeInTheDocument();
  });

  it("renders the how it works section with all three steps", () => {
    renderHome();

    expect(screen.getByText("How it works")).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        level: 2,
        name: /a simpler path through the job mess/i,
      })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("heading", { level: 3, name: /read the resume/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: /score the listings/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: /track progress/i })
    ).toBeInTheDocument();

    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
    expect(screen.getByText("03")).toBeInTheDocument();
  });

  it("renders the future tools section and upcoming feature list", () => {
    renderHome();

    expect(screen.getByText(/what is coming next/i)).toBeInTheDocument();

    expect(
      screen.getByRole("heading", {
        level: 2,
        name: /a growing toolkit for job seekers/i,
      })
    ).toBeInTheDocument();

    const upcomingFeatures = screen.getByLabelText(/upcoming features/i);

    expect(
      within(upcomingFeatures).getByText(/jobs page with fit labels and filters/i)
    ).toBeInTheDocument();
    expect(
      within(upcomingFeatures).getByText(/resume upload and skill extraction/i)
    ).toBeInTheDocument();
    expect(
      within(upcomingFeatures).getByText(/application tracker with status updates/i)
    ).toBeInTheDocument();
  });

  it("renders the future tools illustration with accessible alt text", () => {
    renderHome();

    expect(
      screen.getByRole("img", {
        name: /bloombug user interface mascot illustration/i,
      })
    ).toBeInTheDocument();
  });
});