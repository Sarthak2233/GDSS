import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, it, expect, vi } from "vitest";

expect.extend(toHaveNoViolations);

const { NeighborRankPanel } = await import(
  "@/components/embedding/neighbor-rank-panel"
);

describe("NeighborRankPanel", () => {
  it("renders ranked hits with scores and fires neighbor select", () => {
    const onSelect = vi.fn();
    render(
      <NeighborRankPanel
        querySymbol="ASTParser"
        hits={[
          {
            id: "TransformExtractor",
            name: "TransformExtractor",
            score: 0.95,
            location: "extractor.py",
          },
        ]}
        onSelect={onSelect}
      />
    );
    expect(screen.getByText(/Nearest neighbors/i)).toBeDefined();
    expect(screen.getByText("TransformExtractor")).toBeDefined();
    expect(screen.getByText("95%")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: /TransformExtractor/i }));
    expect(onSelect).toHaveBeenCalledWith("TransformExtractor");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <NeighborRankPanel querySymbol="ASTParser" hits={[]} onSelect={() => {}} />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
