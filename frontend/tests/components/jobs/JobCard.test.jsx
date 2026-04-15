import React from "react";
import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import JobCard from "../../../src/components/jobs/JobCard";

describe("JobCard", () => {
  const baseJob = {
    id: "job-1",
    title: "Junior Frontend Engineer",
    company: "Bloom Labs",
    fitTag: "Real Junior",
    matchScore: 87,
    source: "greenhouse",
    sourceUrl: "https://example.com/job-1",
    url: "https://example.com/job-1",
    cardMeta: ["Atlanta, GA", "Junior", "Remote"],
  };

  it("renders the core job information", () => {
    render(<JobCard job={baseJob} />);

    expect(screen.getByText("Junior Frontend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Bloom Labs")).toBeInTheDocument();
    expect(screen.getByText("Real Junior")).toBeInTheDocument();
    expect(screen.getByLabelText("87 percent match")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Quick view" })).toBeInTheDocument();

    expect(screen.getByText("Atlanta, GA")).toBeInTheDocument();
    expect(screen.getByText("Junior")).toBeInTheDocument();
    expect(screen.getByText("Remote")).toBeInTheDocument();
  });

  it("renders the main surface button with the expected accessible name", () => {
    render(<JobCard job={baseJob} />);

    expect(
      screen.getByRole("button", {
        name: "Open details for Junior Frontend Engineer at Bloom Labs",
      })
    ).toBeInTheDocument();
  });

  it("renders the default quick take for Real Junior roles", () => {
    render(<JobCard job={baseJob} />);

    expect(
      screen.getByText("Looks realistically junior-friendly.")
    ).toBeInTheDocument();
  });

  it("renders qualification signal text when provided", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          qualificationSignal: {
            text: "Role is explicitly framed as early-career friendly.",
          },
        }}
      />
    );

    expect(
      screen.getByText("Role is explicitly framed as early-career friendly.")
    ).toBeInTheDocument();
  });

  it("renders the default quick take for Stretch Role", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          fitTag: "Stretch Role",
        }}
      />
    );

    expect(
      screen.getByText("Possible fit, but double-check requirements.")
    ).toBeInTheDocument();
  });

  it("renders the default quick take for Misleading Junior", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          fitTag: "Misleading Junior",
        }}
      />
    );

    expect(
      screen.getByText("Labeled junior, but parts may lean more experienced.")
    ).toBeInTheDocument();
  });

  it("renders the default quick take fallback for Too Senior roles", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          fitTag: "Too Senior",
        }}
      />
    );

    expect(
      screen.getByText("This may be more experienced than it first appears.")
    ).toBeInTheDocument();
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

  it("calls onOpenDetails when Quick view is clicked", () => {
    const onOpenDetails = vi.fn();

    render(<JobCard job={baseJob} onOpenDetails={onOpenDetails} />);

    fireEvent.click(screen.getByRole("button", { name: "Quick view" }));

    expect(onOpenDetails).toHaveBeenCalledTimes(1);
    expect(onOpenDetails).toHaveBeenCalledWith(baseJob);
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

  it("falls back to safe defaults for invalid fitTag and high matchScore", () => {
    render(
      <JobCard
        job={{
          id: "job-2",
          title: "Mystery Role",
          company: "Unknown Co",
          fitTag: "Not A Real Tag",
          matchScore: 999,
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
        }}
      />
    );

    expect(screen.getByLabelText("0 percent match")).toBeInTheDocument();
  });

  it("renders all cardMeta items", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          cardMeta: ["One", "Two", "Three", "Four", "Five", "Six", "Seven"],
        }}
      />
    );

    expect(screen.getByText("One")).toBeInTheDocument();
    expect(screen.getByText("Six")).toBeInTheDocument();
    expect(screen.getByText("Seven")).toBeInTheDocument();
  });

  it("does not render metadata section when cardMeta is missing", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          cardMeta: undefined,
        }}
      />
    );

    expect(screen.queryByLabelText("Job metadata")).not.toBeInTheDocument();
  });

  it("does not render metadata section when cardMeta is not an array", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          cardMeta: "not-an-array",
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

    fireEvent.click(screen.getByRole("button", { name: "Hide job" }));

    expect(onHide).toHaveBeenCalledTimes(1);
    expect(onHide).toHaveBeenCalledWith(baseJob);
  });

  it("uses custom hide label when provided", () => {
    render(<JobCard job={baseJob} hideLabel="Archive" />);

    expect(
      screen.getByRole("button", { name: "Archive" })
    ).toBeInTheDocument();
  });

  it("shows restore label when the job is hidden", () => {
    render(
      <JobCard
        job={{
          ...baseJob,
          isHidden: true,
        }}
      />
    );

    expect(
      screen.getByRole("button", { name: "Restore job" })
    ).toBeInTheDocument();
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

    expect(screen.getByRole("button", { name: "Hide job" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Hide job" }));

    expect(onHide).not.toHaveBeenCalled();
  });

  it("does not open details when clicking save", () => {
    const onOpenDetails = vi.fn();
    const onSaveToggle = vi.fn();

    render(
      <JobCard
        job={baseJob}
        onOpenDetails={onOpenDetails}
        onSaveToggle={onSaveToggle}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Save job" }));

    expect(onSaveToggle).toHaveBeenCalledTimes(1);
    expect(onOpenDetails).not.toHaveBeenCalled();
  });

  it("does not open details when clicking hide", () => {
    const onOpenDetails = vi.fn();
    const onHide = vi.fn();

    render(
      <JobCard
        job={baseJob}
        onOpenDetails={onOpenDetails}
        onHide={onHide}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: "Hide job" }));

    expect(onHide).toHaveBeenCalledTimes(1);
    expect(onOpenDetails).not.toHaveBeenCalled();
  });
});