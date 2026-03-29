import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../../../src/components/Navbar";

describe("Navbar", () => {
  function renderWithRouter() {
    return render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    );
  }

  it("renders brand icon and text", () => {
    renderWithRouter();

    expect(
      screen.getByAltText("Bloombug EarlyBloom mascot icon")
    ).toBeInTheDocument();

    expect(screen.getByText("EarlyBloom")).toBeInTheDocument();
    expect(
      screen.getByText("Real roles for early careers")
    ).toBeInTheDocument();
  });

  it("links brand to home page", () => {
    renderWithRouter();

    const brandLink = screen.getByRole("link", {
      name: "EarlyBloom home",
    });

    expect(brandLink).toHaveAttribute("href", "/");
  });

  it("renders navigation links", () => {
    renderWithRouter();

    expect(screen.getByText("How It Works")).toBeInTheDocument();
    expect(screen.getByText("Jobs")).toBeInTheDocument();
    expect(screen.getByText("Tools")).toBeInTheDocument();
  });

  it("jobs link points to /jobs route", () => {
    renderWithRouter();

    const jobsLink = screen.getByRole("link", { name: "Jobs" });

    expect(jobsLink).toHaveAttribute("href", "/jobs");
  });

  it("renders anchor links for sections", () => {
    renderWithRouter();

    const missionLink = screen.getByRole("link", {
      name: "How It Works",
    });

    const toolsLink = screen.getByRole("link", {
      name: "Tools",
    });

    expect(missionLink).toHaveAttribute("href", "#mission");
    expect(toolsLink).toHaveAttribute("href", "#future-tools");
  });
});