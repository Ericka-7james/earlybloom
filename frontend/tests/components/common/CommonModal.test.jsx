import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import CommonModal from "../../../src/components/common/CommonModal";

describe("CommonModal", () => {
  it("renders nothing when closed", () => {
    const { container } = render(
      <CommonModal
        isOpen={false}
        title="Hidden modal"
        onClose={() => {}}
      >
        <p>Modal content</p>
      </CommonModal>
    );

    expect(container.firstChild).toBeNull();
  });

  it("renders title and children when open", () => {
    render(
      <CommonModal
        isOpen={true}
        title="Test modal"
        onClose={() => {}}
      >
        <p>Modal content</p>
      </CommonModal>
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Test modal")).toBeInTheDocument();
    expect(screen.getByText("Modal content")).toBeInTheDocument();
  });

  it("calls onClose when overlay is clicked", () => {
    const onClose = vi.fn();

    render(
      <CommonModal
        isOpen={true}
        title="Test modal"
        onClose={onClose}
      >
        <p>Modal content</p>
      </CommonModal>
    );

    const closeButtons = screen.getAllByRole("button", { name: "Close modal" });
    fireEvent.click(closeButtons[0]);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();

    render(
      <CommonModal
        isOpen={true}
        title="Test modal"
        onClose={onClose}
      >
        <p>Modal content</p>
      </CommonModal>
    );

    const closeButtons = screen.getAllByRole("button", { name: "Close modal" });
    fireEvent.click(closeButtons[1]);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when Escape is pressed", () => {
    const onClose = vi.fn();

    render(
      <CommonModal
        isOpen={true}
        title="Test modal"
        onClose={onClose}
      >
        <p>Modal content</p>
      </CommonModal>
    );

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("locks body scroll while open and restores it on unmount", () => {
    document.body.style.overflow = "auto";

    const { unmount } = render(
      <CommonModal
        isOpen={true}
        title="Scroll lock modal"
        onClose={() => {}}
      >
        <p>Modal content</p>
      </CommonModal>
    );

    expect(document.body.style.overflow).toBe("hidden");

    unmount();

    expect(document.body.style.overflow).toBe("auto");
  });

  it("renders the icon when iconImage is provided", () => {
    render(
      <CommonModal
        isOpen={true}
        title="Icon modal"
        onClose={() => {}}
        iconImage="/test-icon.png"
        iconAlt="Test icon"
      >
        <p>Modal content</p>
      </CommonModal>
    );

    expect(screen.getByAltText("Test icon")).toBeInTheDocument();
  });

  it("applies the correct size modifier class", () => {
    const { container } = render(
      <CommonModal
        isOpen={true}
        title="Large modal"
        onClose={() => {}}
        size="lg"
      >
        <p>Modal content</p>
      </CommonModal>
    );

    expect(
      container.querySelector(".common-modal__panel--lg")
    ).toBeInTheDocument();
  });
});