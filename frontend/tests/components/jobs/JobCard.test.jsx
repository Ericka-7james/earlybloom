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

  it("renders the core job information", () => {
    render(<JobCard job={baseJob} />);

    expect(screen.getByText("Junior Frontend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Bloom Labs")).toBeInTheDocument();
    expect(screen.getByText("Atlanta, GA")).toBeInTheDocument();
    expect(screen.getByText("Real Junior")).toBeInTheDocument();
    expect(screen.getByText("Junior")).toBeInTheDocument();
    expect(screen.getByText("Source: Greenhouse")).toBeInTheDocument();
    expect(screen.getByLabelText("87 percent match")).toBeInTheDocument();
    expect(
      screen.getByText("Build polished UI for early-career job seekers.")
    ).toBeInTheDocument();
  });

  it("renders the main surface button with the expected accessible name", () => {
    render(<JobCard job={baseJob} />);

    expect(
      screen.getByRole("button", {
        name: "Open details for Junior Frontend Engineer at Bloom Labs",
      })
    ).toBeInTheDocument();
  });

  it("shows the Why preview block using the first reason", () => {
    render(<JobCard job={baseJob} />);

    expect(screen.getByText("Why")).toBeInTheDocument();
    expect(screen.getByText("Entry-level title")).toBeInTheDocument();
  });

  it("calls onOpenReasonsModal when the card surface is clicked", () => {
    const onOpenReasonsModal = vi.fn();

    render(
      <JobCard job={baseJob} onOpenReasonsModal={onOpenReasonsModal} />
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Open details for Junior Frontend Engineer at Bloom Labs",
      })
    );

    expect(onOpenReasonsModal).toHaveBeenCalledTimes(1);
    expect(onOpenReasonsModal).toHaveBeenCalledWith(baseJob);
  });

  it("shows watchout text when there are warning flags even without reasons", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          reasons: [],
          warningFlags: ["Asks for 3+ years"],
        }}
        onOpenReasonsModal={() => {}}
      />
    );

    expect(screen.getByText("Includes watchouts")).toBeInTheDocument();
  });

  it("does not show the Why preview block when there are no reasons", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          reasons: [],
          warningFlags: [],
        }}
        onOpenReasonsModal={() => {}}
      />
    );

    expect(screen.queryByText("Why")).not.toBeInTheDocument();
    expect(screen.queryByText("Entry-level title")).not.toBeInTheDocument();
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
          reasons: [],
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
          reasons: [],
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
          reasons: [],
          warningFlags: [],
        }}
      />
    );

    expect(screen.getByLabelText("0 percent match")).toBeInTheDocument();
  });

  it("does not render the summary when it is empty", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          summary: "   ",
        }}
      />
    );

    expect(
      screen.queryByText("Build polished UI for early-career job seekers.")
    ).not.toBeInTheDocument();
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
          reasons: [],
          warningFlags: [],
        }}
      />
    );

    expect(screen.getByText("Untitled role")).toBeInTheDocument();
    expect(screen.getByText("Unknown company")).toBeInTheDocument();
    expect(screen.getByText("Location not listed")).toBeInTheDocument();
  });

  it("supports snake_case experience level fields", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          experienceLevel: undefined,
          experience_level: "mid-level",
        }}
      />
    );

    expect(screen.getByText("Mid-level")).toBeInTheDocument();
  });
});