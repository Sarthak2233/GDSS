import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "jest-axe";
import { CommutativityTable } from "../../components/tensor/commutativity-table";
import type { CommutativityPair } from "../../lib/api-types";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

const pairs: CommutativityPair[] = [
  { a: "rename_function", b: "delete_function", class: "interfere" },
  { a: "modify_function", b: "modify_function", class: "commute" },
  { a: "add_function", b: "rename_class", class: "interfere" },
];

describe("CommutativityTable", () => {
  it("defaults to INTERFERE pairs and shows deterministic badge", () => {
    render(<CommutativityTable pairs={pairs} />);

    expect(screen.getByTestId("commutativity-table")).toBeInTheDocument();
    expect(screen.getByTestId("evidence-phase-badge")).toHaveAttribute(
      "data-phase",
      "deterministic"
    );
    expect(screen.getByText("rename_function")).toBeInTheDocument();
    expect(screen.queryByText("modify_function")).not.toBeInTheDocument();
  });

  it("can show all classes when filter cleared", () => {
    render(<CommutativityTable pairs={pairs} />);
    fireEvent.click(screen.getByRole("button", { name: /all/i }));
    expect(screen.getAllByText("modify_function").length).toBeGreaterThan(0);
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<CommutativityTable pairs={pairs} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
