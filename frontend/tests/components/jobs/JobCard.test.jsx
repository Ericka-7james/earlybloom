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
    metadata: ["Atlanta, GA", "Junior", "Source: Greenhouse"],
  };

  it("renders the core compact job information", () => {
    render(<JobCard job={baseJob} />);

    expect(screen.getByText("Junior Frontend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Bloom Labs")).toBeInTheDocument();
    expect(screen.getByText("Real Junior")).toBeInTheDocument();
    expect(screen.getByLabelText("87 percent match")).toBeInTheDocument();
    expect(screen.getByText("View details")).toBeInTheDocument();

    expect(screen.getByText("Atlanta, GA")).toBeInTheDocument();
    expect(screen.getByText("Junior")).toBeInTheDocument();
    expect(screen.getByText("Source: Greenhouse")).toBeInTheDocument();
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

  it("calls onOpenDetails when view details is clicked", () => {
    const onOpenDetails = vi.fn();

    render(<JobCard job={baseJob} onOpenDetails={onOpenDetails} />);

    fireEvent.click(screen.getByRole("button", { name: "View details" }));

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

  it("shows saved chip when the job is saved", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          isSaved: true,
        }}
      />
    );

    expect(screen.getByText("Saved")).toBeInTheDocument();
  });

  it("falls back to safe defaults for invalid fitTag and matchScore", () => {
    render(
      <JobCard
        job={{
          id: "job-2",
          title: "Mystery Role",
          company: "Unknown Co",
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
          fitTag: "Stretch Role",
          warningFlags: [],
        }}
      />
    );

    expect(screen.getByLabelText("0 percent match")).toBeInTheDocument();
  });

  it("renders up to six metadata items", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          metadata: ["One", "Two", "Three", "Four", "Five", "Six", "Seven"],
        }}
      />
    );

    expect(screen.getByText("One")).toBeInTheDocument();
    expect(screen.getByText("Six")).toBeInTheDocument();
    expect(screen.queryByText("Seven")).not.toBeInTheDocument();
  });

  it("does not render metadata section when metadata is missing", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          metadata: undefined,
        }}
      />
    );

    expect(screen.queryByLabelText("Job metadata")).not.toBeInTheDocument();
  });

  it("renders default title and company when missing", () => {
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
  });

  it("uses url for the apply link when present", () => {
    render(<JobCard job={baseJob} />);

    const applyLink = screen.getByRole("link", { name: "Apply" });
    expect(applyLink).toHaveAttribute("href", "https://example.com/job-1");
    expect(applyLink).toHaveAttribute("target", "_blank");
    expect(applyLink).toHaveAttribute("rel", "noreferrer");
  });

  it("falls back to sourceUrl for the apply link when url is missing", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          url: null,
          sourceUrl: "https://example.com/source-only",
        }}
      />
    );

    const applyLink = screen.getByRole("link", { name: "Apply" });
    expect(applyLink).toHaveAttribute("href", "https://example.com/source-only");
  });

  it("renders apply as a button when no external url is available", () => {
    const onOpenDetails = vi.fn();

    render(
      <JobCard
        job={{
          ...baseJob,
          url: null,
          sourceUrl: null,
        }}
        onOpenDetails={onOpenDetails}
      />
    );

    const applyButton = screen.getByRole("button", { name: "Apply" });
    fireEvent.click(applyButton);

    expect(onOpenDetails).toHaveBeenCalledTimes(1);
    expect(onOpenDetails).toHaveBeenCalledWith({
      ...baseJob,
      url: null,
      sourceUrl: null,
    });
  });

  it("calls onSaveToggle when save button is clicked", () => {
    const onSaveToggle = vi.fn();

    render(<JobCard job={baseJob} onSaveToggle={onSaveToggle} />);

    fireEvent.click(screen.getByRole("button", { name: "Save job" }));

    expect(onSaveToggle).toHaveBeenCalledTimes(1);
    expect(onSaveToggle).toHaveBeenCalledWith(baseJob);
  });

  it("does not call onSaveToggle when save is pending", () => {
    const onSaveToggle = vi.fn();

    render(
      <JobCard
        job={baseJob}
        onSaveToggle={onSaveToggle}
        isSavePending={true}
      />
    );

    expect(screen.getByRole("button", { name: "Save job" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Save job" }));

    expect(onSaveToggle).not.toHaveBeenCalled();
  });

  it("shows remove saved job label when the job is already saved", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          isSaved: true,
        }}
      />
    );

    expect(
      screen.getByRole("button", { name: "Remove saved job" })
    ).toBeInTheDocument();
  });

  it("calls onHide when hide button is clicked", () => {
    const onHide = vi.fn();

    render(<JobCard job={baseJob} onHide={onHide} />);

    fireEvent.click(screen.getByRole("button", { name: "Hide" }));

    expect(onHide).toHaveBeenCalledTimes(1);
    expect(onHide).toHaveBeenCalledWith(baseJob);
  });

  it("uses custom hide label when provided", () => {
    render(<JobCard job={baseJob} hideLabel="Archive" />);

    expect(
      screen.getByRole("button", { name: "Archive" })
    ).toBeInTheDocument();
  });

  it("shows hidden state label when the job is hidden", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          isHidden: true,
        }}
      />
    );

    expect(screen.getByRole("button", { name: "Hidden" })).toBeInTheDocument();
  });

  it("does not call onHide when hide is pending", () => {
    const onHide = vi.fn();

    render(
      <JobCard
        job={baseJob}
        onHide={onHide}
        isHidePending={true}
      />
    );

    expect(screen.getByRole("button", { name: "Hide" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Hide" }));

    expect(onHide).not.toHaveBeenCalled();
  });
});