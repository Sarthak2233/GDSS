import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, it, expect, vi } from "vitest";

expect.extend(toHaveNoViolations);

const { NodeDetailPanel } = await import(
  "@/components/constellation/node-detail-panel"
);

const mockNode = {
  id: "gdss/core/ast_parser.py::ASTParser",
  name: "ASTParser",
  type: "class",
  location: "gdss/core/ast_parser.py",
};

const mockSimilarHits = [
  {
    id: "gdss/core/transform_extractor.py::TransformExtractor",
    score: 0.94,
    name: "TransformExtractor",
    location: "gdss/core/transform_extractor.py",
  },
  {
    id: "gdss/core/trajectory.py::extract_trajectory_operators",
    score: 0.82,
    name: "extract_trajectory_operators",
    location: "gdss/core/trajectory.py",
  },
];

describe("NodeDetailPanel component", () => {
  it("renders nothing when node is null", () => {
    const { container } = render(
      <NodeDetailPanel node={null} onClose={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders node details (name, type, location)", () => {
    render(
      <NodeDetailPanel
        node={mockNode}
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText("ASTParser")).toBeDefined();
    expect(screen.getByText("class")).toBeDefined();
    expect(screen.getByText("gdss/core/ast_parser.py")).toBeDefined();
  });

  it("renders similarity hits when provided and handles neighbor select", () => {
    const onNeighborSelect = vi.fn();
    render(
      <NodeDetailPanel
        node={mockNode}
        similarHits={mockSimilarHits}
        onClose={vi.fn()}
        onNeighborSelect={onNeighborSelect}
      />
    );

    expect(screen.getByText("Similar Symbols (2)")).toBeDefined();
    const neighborBtn = screen.getByText("TransformExtractor");
    expect(neighborBtn).toBeDefined();
    expect(screen.getByText("94%")).toBeDefined();

    fireEvent.click(neighborBtn);
    expect(onNeighborSelect).toHaveBeenCalledWith(
      "gdss/core/transform_extractor.py::TransformExtractor"
    );
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<NodeDetailPanel node={mockNode} onClose={onClose} />);
    const closeBtn = screen.getByLabelText("Close details panel");
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("renders connected symbols and handles connected select", () => {
    const onConnectedSelect = vi.fn();
    const mockConnected = [
      { id: "utils.py::helper", name: "helper", type: "function", relationship: "calls" },
      { id: "os::path", name: "path", type: "module_dependency", relationship: "imports" },
    ];
    render(
      <NodeDetailPanel
        node={mockNode}
        connectedSymbols={mockConnected}
        onClose={vi.fn()}
        onConnectedSelect={onConnectedSelect}
      />
    );

    expect(screen.getByText("Connected Symbols (2)")).toBeDefined();
    const connBtn = screen.getByText("helper");
    expect(connBtn).toBeDefined();

    fireEvent.click(connBtn);
    expect(onConnectedSelect).toHaveBeenCalledWith("utils.py::helper");
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <NodeDetailPanel
        node={mockNode}
        similarHits={mockSimilarHits}
        onClose={vi.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

