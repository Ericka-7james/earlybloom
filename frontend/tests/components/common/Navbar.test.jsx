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

  it("renders desktop primary navigation for signed out users", () => {
    renderWithRouter();

    const nav = screen.getByRole("navigation", {
      name: "Primary navigation",
    });

    expect(
      screen.getAllByRole("link", { name: "Home" }).length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("link", { name: "Jobs" }).length
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole("link", { name: "Learn More" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Sign in" })
    ).toBeInTheDocument();

    expect(nav).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Tracker" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Profile" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Sign out" })
    ).not.toBeInTheDocument();
  });

  it("jobs link points to /jobs route", () => {
    renderWithRouter();

    const jobsLinks = screen.getAllByRole("link", { name: "Jobs" });
    expect(jobsLinks[0]).toHaveAttribute("href", "/jobs");
  });

  it("learn more link points to /learn-more route for guests", () => {
    renderWithRouter();

    const learnMoreLink = screen.getByRole("link", { name: "Learn More" });
    expect(learnMoreLink).toHaveAttribute("href", "/learn-more");
  });

  it("renders authenticated navigation when user is signed in", () => {
    useAuth.mockReturnValue({
      user: { email: "test@example.com" },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    expect(
      screen.getAllByRole("link", { name: "Home" }).length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("link", { name: "Jobs" }).length
    ).toBeGreaterThan(0);
    expect(
      screen.getByRole("link", { name: "Tracker" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Profile" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign out" })
    ).toBeInTheDocument();

    expect(
      screen.queryByRole("link", { name: "Learn More" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Sign in" })
    ).not.toBeInTheDocument();
  });

  it("shows checking sign in label while auth state is loading", () => {
    useAuth.mockReturnValue({
      user: null,
      loading: true,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    expect(
      screen.getByRole("link", { name: "EarlyBloom home" })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Checking sign in..." })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("link", { name: "Home" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Jobs" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Learn More" })
    ).toBeInTheDocument();

    expect(
      screen.getByRole("button", {
        name: "Open navigation menu",
      })
    ).toBeInTheDocument();
  });

  it("opens the mobile menu when trigger is clicked", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    const menuButton = screen.getByRole("button", {
      name: "Open navigation menu",
    });

    expect(menuButton).toHaveAttribute("aria-expanded", "false");

    await user.click(menuButton);

    expect(menuButton).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByRole("button", { name: "Close navigation menu" })
    ).toBeInTheDocument();
    expect(screen.getByRole("menu")).toBeInTheDocument();
  });

  it("renders guest mobile menu items when menu is opened", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    await user.click(
      screen.getByRole("button", { name: "Open navigation menu" })
    );

    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Home" }).length
    ).toBeGreaterThan(1);
    expect(
      screen.getAllByRole("link", { name: "Jobs" }).length
    ).toBeGreaterThan(1);
    expect(
      screen.getAllByRole("link", { name: "Learn More" }).length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("link", { name: "Sign in" }).length
    ).toBeGreaterThan(0);
  });

  it("renders authenticated mobile menu items when menu is opened", async () => {
    const user = userEvent.setup();

    useAuth.mockReturnValue({
      user: { email: "test@example.com" },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    await user.click(
      screen.getByRole("button", { name: "Open navigation menu" })
    );

    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "Tracker" }).length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("link", { name: "Profile" }).length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByRole("button", { name: "Sign out" }).length
    ).toBeGreaterThan(0);
  });

  it("calls handleSignOut and navigates home when sign out is clicked", async () => {
    const user = userEvent.setup();

    mockHandleSignOut.mockResolvedValue(undefined);

    useAuth.mockReturnValue({
      user: { email: "test@example.com" },
      loading: false,
      handleSignOut: mockHandleSignOut,
    });

    renderWithRouter();

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(mockHandleSignOut).toHaveBeenCalledTimes(1);
      expect(mockNavigate).toHaveBeenCalledWith("/");
    });
  });

  it("closes the mobile menu when escape is pressed", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    await user.click(
      screen.getByRole("button", { name: "Open navigation menu" })
    );

    expect(screen.getByRole("menu")).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes the mobile menu when clicking outside", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    await user.click(
      screen.getByRole("button", { name: "Open navigation menu" })
    );

    expect(screen.getByRole("menu")).toBeInTheDocument();

    fireEvent.mouseDown(document.body);

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes the mobile menu when a mobile nav link is clicked", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    await user.click(
      screen.getByRole("button", { name: "Open navigation menu" })
    );

    const homeLinks = screen.getAllByRole("link", { name: "Home" });
    const mobileHomeLink = homeLinks[homeLinks.length - 1];

    await user.click(mobileHomeLink);

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("toggles the mobile menu closed when trigger is clicked again", async () => {
    const user = userEvent.setup();
    renderWithRouter();

    const trigger = screen.getByRole("button", {
      name: "Open navigation menu",
    });

    await user.click(trigger);
    expect(screen.getByRole("menu")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Close navigation menu" })
    );

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});