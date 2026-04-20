import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  });

  it("links brand to home page", () => {
    renderWithRouter();

    const brandLink = screen.getByRole("link", {
      name: "EarlyBloom home",
    });

    expect(brandLink).toHaveAttribute("href", "/");
  });

  it("renders the jobs search icon button", () => {
    renderWithRouter();

    expect(
      screen.getByRole("button", { name: "Go to jobs search" })
    ).toBeInTheDocument();
  });

  it("navigates to jobs when search icon is clicked", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    await user.click(screen.getByRole("button", { name: "Go to jobs search" }));

    expect(mockNavigate).toHaveBeenCalledWith("/jobs");
  });

  it("renders guest auth links", () => {
    renderWithRouter();

    expect(screen.getByRole("link", { name: "Join" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows checking label while loading", () => {
    useAuth.mockReturnValue({
      user: null,
      loading: true,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    expect(screen.getByRole("link", { name: "Checking..." })).toBeInTheDocument();
  });

  it("renders navigation sections", () => {
    renderWithRouter();

    expect(
      screen.getByRole("navigation", { name: "Primary navigation" })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("navigation", { name: "Mobile navigation" })
    ).toBeInTheDocument();
  });

  it("renders signed-in avatar instead of auth links", () => {
    useAuth.mockReturnValue({
      user: {
        email: "test@example.com",
        user_metadata: { name: "Ericka", avatar: "petaloo" },
      },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    expect(screen.queryByText("Join")).not.toBeInTheDocument();
    expect(screen.queryByText("Sign in")).not.toBeInTheDocument();

    expect(
      screen.getByRole("button", { name: "Open profile menu" })
    ).toBeInTheDocument();
  });

  it("opens profile menu", async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValue({
      user: {
        email: "test@example.com",
        user_metadata: { name: "Ericka", avatar: "petaloo" },
      },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));

    expect(
      screen.getByRole("menuitem", { name: "Profile" })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("menuitem", { name: "Sign out" })
    ).toBeInTheDocument();
  });

  it("navigates to profile", async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValue({
      user: {
        email: "test@example.com",
        user_metadata: { name: "Ericka", avatar: "petaloo" },
      },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.click(screen.getByRole("menuitem", { name: "Profile" }));

    expect(mockNavigate).toHaveBeenCalledWith("/profile");
  });

  it("signs out and redirects", async () => {
    const user = userEvent.setup();

    mockHandleSignOut.mockResolvedValue();

    useAuth.mockReturnValue({
      user: {
        email: "test@example.com",
        user_metadata: { name: "Ericka", avatar: "petaloo" },
      },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.click(screen.getByRole("menuitem", { name: "Sign out" }));

    await waitFor(() => {
      expect(mockHandleSignOut).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });

  it("closes menu on escape", async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValue({
      user: {
        email: "test@example.com",
        user_metadata: { name: "Ericka", avatar: "petaloo" },
      },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));
    await user.keyboard("{Escape}");

    expect(
      screen.queryByRole("menuitem", { name: "Profile" })
    ).not.toBeInTheDocument();
  });

  it("closes menu on outside click", async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValue({
      user: {
        email: "test@example.com",
        user_metadata: { name: "Ericka", avatar: "petaloo" },
      },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    await user.click(screen.getByRole("button", { name: "Open profile menu" }));

    fireEvent.mouseDown(document.body);

    expect(
      screen.queryByRole("menuitem", { name: "Profile" })
    ).not.toBeInTheDocument();
  });
});