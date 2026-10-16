import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "jest-axe";
import { OmegaCellDetail } from "../../components/tensor/omega-cell-detail";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

describe("OmegaCellDetail", () => {
  it("shows omega, reasons, and branch pair with drift link", () => {
    render(
      <OmegaCellDetail
        i="feature"
        j="main"
        omega={0.42}
        reasons={["same_file", "interference=1.00"]}
      />
    );

    expect(screen.getByTestId("omega-cell-detail")).toBeInTheDocument();
    expect(screen.getByText(/feature/)).toBeInTheDocument();
    expect(screen.getByText(/main/)).toBeInTheDocument();
    expect(screen.getByText(/0\.42/)).toBeInTheDocument();
    expect(screen.getByText(/same_file/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /drift/i })).toHaveAttribute(
      "href",
      "/drift"
    );
  });

  it("shows empty prompt when no cell selected", () => {
    render(<OmegaCellDetail i={null} j={null} omega={null} reasons={[]} />);
    expect(screen.getByText(/select a cell/i)).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <OmegaCellDetail
        i="feature"
        j="main"
        omega={0.1}
        reasons={["drift_self_energy"]}
      />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
