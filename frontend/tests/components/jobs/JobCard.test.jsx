import React from "react";
import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import JobCard from "../../../src/components/jobs/JobCard";

describe("JobCard", () => {
  const baseJob = {
    id: "job-1",
    title: "Junior Frontend Engineer",
    company: "Bloom Labs",
    location: "Atlanta, GA",
    experienceLevel: "junior",
    summary: "Build polished UI for early-career job seekers.",
    fitTag: "Real Junior",
    matchScore: 87,
    reasons: ["Entry-level title", "React experience aligns"],
    warningFlags: [],
    source: "greenhouse",
    sourceUrl: "https://example.com/job-1",
    url: "https://example.com/job-1",
  };

  it("renders the core compact job information", () => {
    render(<JobCard job={baseJob} />);

    expect(screen.getByText("Junior Frontend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Bloom Labs")).toBeInTheDocument();
    expect(screen.getByText("Atlanta, GA")).toBeInTheDocument();
    expect(screen.getByText("Real Junior")).toBeInTheDocument();
    expect(screen.getByText("Junior")).toBeInTheDocument();
    expect(screen.getByText("Source: Greenhouse")).toBeInTheDocument();
    expect(screen.getByLabelText("87 percent match")).toBeInTheDocument();
    expect(screen.getByText("View details")).toBeInTheDocument();
  });

  it("renders the main surface button with the expected accessible name", () => {
    render(<JobCard job={baseJob} />);

    expect(
      screen.getByRole("button", {
        name: "Open details for Junior Frontend Engineer at Bloom Labs",
      })
    ).toBeInTheDocument();
  });

  it("does not render the summary preview on the card", () => {
    render(<JobCard job={baseJob} />);

    expect(
      screen.queryByText("Build polished UI for early-career job seekers.")
    ).not.toBeInTheDocument();
  });

  it("does not render the old Why preview block", () => {
    render(<JobCard job={baseJob} />);

    expect(screen.queryByText("Why")).not.toBeInTheDocument();
    expect(screen.queryByText("Entry-level title")).not.toBeInTheDocument();
  });

  it("calls onOpenDetails when the card surface is clicked", () => {
    const onOpenDetails = vi.fn();

    render(<JobCard job={baseJob} onOpenDetails={onOpenDetails} />);

    fireEvent.click(
      screen.getByRole("button", {
        name: "Open details for Junior Frontend Engineer at Bloom Labs",
      })
    );

    expect(onOpenDetails).toHaveBeenCalledTimes(1);
    expect(onOpenDetails).toHaveBeenCalledWith(baseJob);
  });

  it("shows watchout chip when there are warning flags", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          warningFlags: ["Asks for 3+ years"],
        }}
      />
    );

    expect(screen.getByText("Watchouts")).toBeInTheDocument();
  });

  it("does not show the watchout chip when there are no warning flags", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          warningFlags: [],
        }}
      />
    );

    expect(screen.queryByText("Watchouts")).not.toBeInTheDocument();
  });

  it("falls back to safe defaults for invalid fitTag and matchScore", () => {
    render(
      <JobCard
        job={{
          id: "job-2",
          title: "Mystery Role",
          company: "Unknown Co",
          location: "Remote",
          fitTag: "Not A Real Tag",
          matchScore: 999,
          warningFlags: [],
        }}
      />
    );

    expect(screen.getByText("Too Senior")).toBeInTheDocument();
    expect(screen.getByLabelText("100 percent match")).toBeInTheDocument();
  });

  it("clamps invalid low or missing match scores safely", () => {
    const { rerender } = render(
      <JobCard
        job={{
          id: "job-3",
          title: "Low Score Role",
          company: "Bloom Labs",
          location: "Remote",
          fitTag: "Stretch Role",
          matchScore: -20,
          warningFlags: [],
        }}
      />
    );

    expect(screen.getByLabelText("0 percent match")).toBeInTheDocument();

    rerender(
      <JobCard
        job={{
          id: "job-4",
          title: "Missing Score Role",
          company: "Bloom Labs",
          location: "Remote",
          fitTag: "Stretch Role",
          warningFlags: [],
        }}
      />
    );

    expect(screen.getByLabelText("0 percent match")).toBeInTheDocument();
  });

  it("renders unknown source labels as-is", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          source: "custom-board",
          sourceUrl: null,
          url: null,
        }}
      />
    );

    expect(screen.getByText("Source: custom-board")).toBeInTheDocument();
  });

  it("renders default title, company, and location when missing", () => {
    render(
      <JobCard
        job={{
          id: "job-5",
          warningFlags: [],
        }}
      />
    );

    expect(screen.getByText("Untitled role")).toBeInTheDocument();
    expect(screen.getByText("Unknown company")).toBeInTheDocument();
    expect(screen.getByText("Location not listed")).toBeInTheDocument();
  });

  it("renders compensation in compact metadata when provided", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          compensation: "$85,000 - $100,000",
        }}
      />
    );

    expect(screen.getByText("$85,000 - $100,000")).toBeInTheDocument();
  });

  it("prefers cardLocation over location when provided", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          cardLocation: "Multiple U.S. locations",
          location: "Atlanta, GA; Remote; Washington, DC",
        }}
      />
    );

    expect(screen.getByText("Multiple U.S. locations")).toBeInTheDocument();
    expect(
      screen.queryByText("Atlanta, GA; Remote; Washington, DC")
    ).not.toBeInTheDocument();
  });

  it("does not support snake_case experience level fields", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          experienceLevel: undefined,
          experience_level: "mid-level",
        }}
      />
    );

    expect(screen.queryByText("Mid-level")).not.toBeInTheDocument();
  });
});