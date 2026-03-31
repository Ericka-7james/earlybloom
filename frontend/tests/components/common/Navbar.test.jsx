import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Navbar from "../../../src/components/Navbar";

const mockNavigate = vi.fn();
const mockHandleSignOut = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("../../../src/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "../../../src/hooks/useAuth";

describe("Navbar", () => {
  function renderWithRouter() {
    return render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>
    );
  }

  beforeEach(() => {
    vi.clearAllMocks();

    useAuth.mockReturnValue({
      user: null,
      loading: false,
      handleSignOut: mockHandleSignOut,
    });
  });

  it("renders brand icon and text", () => {
    renderWithRouter();

    expect(
      screen.getByAltText("EarlyBloom Bloombug icon")
    ).toBeInTheDocument();

    expect(screen.getByText("EarlyBloom")).toBeInTheDocument();
    expect(
      screen.getByText("Grow into the right role")
    ).toBeInTheDocument();
  });

  it("links brand to home page", () => {
    renderWithRouter();

    const brandLink = screen.getByRole("link", {
      name: "EarlyBloom home",
    });

    expect(brandLink).toHaveAttribute("href", "/");
  });

  it("renders public navigation links when signed out", () => {
    renderWithRouter();

    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Jobs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign up" })).toBeInTheDocument();
  });

  it("jobs link points to /jobs route", () => {
    renderWithRouter();

    const jobsLink = screen.getByRole("link", { name: "Jobs" });

    expect(jobsLink).toHaveAttribute("href", "/jobs");
  });

  it("renders authenticated navigation when user is signed in", () => {
    useAuth.mockReturnValue({
      user: { email: "test@example.com" },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign out" })
    ).toBeInTheDocument();

    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign up" })).not.toBeInTheDocument();
  });

  it("hides auth actions while loading", () => {
    useAuth.mockReturnValue({
      user: null,
      loading: true,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Jobs" })).toBeInTheDocument();

    expect(screen.queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Sign up" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();
  });
});