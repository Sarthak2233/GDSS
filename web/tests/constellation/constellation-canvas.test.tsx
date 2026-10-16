import React from "react";
import { render, screen, cleanup, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

expect.extend(toHaveNoViolations);

// Mock Three.js canvas (JSDOM has no WebGL)
vi.mock("@react-three/fiber", () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="r3f-canvas">{children}</div>
  ),
  useFrame: vi.fn(),
  useThree: vi.fn(() => ({
    camera: {
      position: {
        set: vi.fn(),
        applyAxisAngle: vi.fn(),
      },
      lookAt: vi.fn(),
    },
    gl: { domElement: document.createElement("canvas") },
  })),
}));

vi.mock("@react-three/drei", () => ({
  OrbitControls: () => null,
  Stars: () => null,
  Html: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="r3f-html-label">{children}</div>
  ),
}));

// Import after mocks
const { ConstellationCanvas } = await import(
  "@/components/constellation/constellation-canvas"
);

const mockNodes = [
  { id: "fn_a", name: "fn_a", type: "function", location: "a.py" },
  { id: "cls_b", name: "ClassB", type: "class", location: "b.py" },
  { id: "os", name: "os", type: "module_dependency", location: "" },
];

const mockEdges = [
  { source: "fn_a", target: "cls_b", relationship: "calls" },
  { source: "fn_a", target: "os", relationship: "imports" },
];

const originalMatchMedia = window.matchMedia;

function mockMatchMedia(reducedMotion: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches:
      query === "(prefers-reduced-motion: reduce)" ? reducedMotion : false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

afterEach(() => {
  cleanup();
  window.matchMedia = originalMatchMedia;
});

describe("ConstellationCanvas component", () => {
  it("renders the 3D canvas container with correct testid", () => {
    mockMatchMedia(false);
    render(
      <ConstellationCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodeSelect={vi.fn()}
      />
    );
    expect(screen.getByTestId("constellation-canvas")).toBeDefined();
  });

  it("renders small node labels for each symbol in 3D canvas mode", () => {
    mockMatchMedia(false);
    render(
      <ConstellationCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodeSelect={vi.fn()}
      />
    );
    const htmlLabels = screen.getAllByTestId("r3f-html-label");
    expect(htmlLabels.length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("fn_a")).toBeDefined();
    expect(screen.getByText("ClassB")).toBeDefined();
    expect(screen.getByText("os")).toBeDefined();
  });

  it("displays the Traversal Trace HUD when a node is selected", () => {
    mockMatchMedia(false);
    const onNodeSelect = vi.fn();
    render(
      <ConstellationCanvas
        nodes={mockNodes}
        edges={mockEdges}
        selectedNodeId="fn_a"
        onNodeSelect={onNodeSelect}
      />
    );
    expect(screen.getByTestId("traversal-trace-hud")).toBeDefined();
    expect(screen.getByText(/Active Traversal Trace:/i)).toBeDefined();
    expect(screen.getByText(/2 connected symbols/i)).toBeDefined();

    const clearBtn = screen.getByRole("button", { name: /Clear Trace/i });
    fireEvent.click(clearBtn);
    expect(onNodeSelect).toHaveBeenCalledWith("");
  });

  it("renders the reduced-motion table fallback when motion is reduced", () => {
    mockMatchMedia(true);
    render(
      <ConstellationCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodeSelect={vi.fn()}
      />
    );
    expect(screen.getByTestId("constellation-table-fallback")).toBeDefined();
    expect(screen.getByText("fn_a")).toBeDefined();
    expect(screen.getByText("ClassB")).toBeDefined();
    expect(screen.getByText("os")).toBeDefined();
  });

  it("displays floating hover tooltip when hovering a node in fallback mode", () => {
    mockMatchMedia(true);
    render(
      <ConstellationCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodeSelect={vi.fn()}
      />
    );
    const row = screen.getByText("fn_a").closest("tr")!;
    fireEvent.mouseEnter(row);
    expect(screen.getByTestId("constellation-hover-tooltip")).toBeDefined();
    expect(screen.getByText("Click sphere to inspect & traverse connections")).toBeDefined();
    fireEvent.mouseLeave(row);
    expect(screen.queryByTestId("constellation-hover-tooltip")).toBeNull();
  });

  it("has no accessibility violations", async () => {
    mockMatchMedia(false);
    const { container } = render(
      <ConstellationCanvas
        nodes={mockNodes}
        edges={mockEdges}
        onNodeSelect={vi.fn()}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
