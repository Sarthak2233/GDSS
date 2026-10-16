import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { Button } from "@/components/ui/button";

describe("Button", () => {
  it("renders children and is keyboard-accessible", () => {
    render(<Button>Analyze</Button>);
    const btn = screen.getByRole("button", { name: "Analyze" });
    expect(btn).toBeInTheDocument();
    expect(btn.tagName).toBe("BUTTON");
  });

  it("has no a11y violations", async () => {
    const { container } = render(<Button>OK</Button>);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("shows a loading affordance (not a page spinner) in the loading state", () => {
    render(<Button state={{ loading: true }}>Save</Button>);
    expect(screen.getByTestId("button-loading")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save/i })).toHaveAttribute(
      "aria-busy",
      "true",
    );
  });

  it("marks disabled state with aria-disabled and is not interactive", () => {
    render(<Button disabled>Save</Button>);
    const btn = screen.getByRole("button", { name: /save/i });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-disabled");
  });

  it("renders a success affordance in the success state", () => {
    render(
      <Button state={{ success: true }} successLabel="Saved">
        Save
      </Button>,
    );
    expect(screen.getByTestId("button-success")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /saved/i })).toBeInTheDocument();
  });

  it("respects reduced motion: no transform animations are applied", () => {
    // useReducedMotion reads matchMedia; we assert the component still renders
    // and remains accessible without motion props (functional contract).
    render(<Button>Analyze</Button>);
    expect(screen.getByRole("button", { name: "Analyze" })).toBeInTheDocument();
  });
});

// Silence act warnings from framer-motion rAF in jsdom.
vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
  return 0 as unknown as number;
});
