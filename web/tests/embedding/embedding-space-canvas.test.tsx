import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, it, expect, vi } from "vitest";

expect.extend(toHaveNoViolations);

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

const { EmbeddingSpaceCanvas } = await import(
  "@/components/embedding/embedding-space-canvas"
);

const points = [
  {
    id: "ASTParser",
    name: "ASTParser",
    type: "class",
    location: "parser.py",
    x: -0.5,
    y: 0.2,
  },
  {
    id: "TransformExtractor",
    name: "TransformExtractor",
    type: "class",
    location: "extractor.py",
    x: 0.4,
    y: -0.1,
  },
];

describe("EmbeddingSpaceCanvas", () => {
  it("renders projected points and selects on click", () => {
    const onSelect = vi.fn();
    render(
      <EmbeddingSpaceCanvas
        points={points}
        selectedId="ASTParser"
        highlightedIds={new Set(["ASTParser", "TransformExtractor"])}
        onSelect={onSelect}
      />
    );
    expect(screen.getByTestId("embedding-space-canvas")).toBeDefined();
    expect(
      screen.getByLabelText(/embedding space projection/i)
    ).toBeDefined();
    const pointBtn = screen.getByRole("button", { name: /ASTParser/i });
    fireEvent.click(pointBtn);
    expect(onSelect).toHaveBeenCalledWith("ASTParser");
  });

  it("shows empty state when there are no points", () => {
    render(
      <EmbeddingSpaceCanvas points={[]} selectedId={null} onSelect={() => {}} />
    );
    expect(screen.getByText(/no embedding points/i)).toBeDefined();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <EmbeddingSpaceCanvas
        points={points}
        selectedId={null}
        highlightedIds={new Set(["TransformExtractor"])}
        onSelect={() => {}}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
