import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

expect.extend(toHaveNoViolations);

// Mock dynamic import of ConstellationCanvas
vi.mock("next/dynamic", () => ({
  default: () => {
    return function MockDynamicCanvas(props: any) {
      return (
        <div data-testid="constellation-canvas">
          <span>Mock 3D Canvas ({props.nodes?.length || 0} nodes)</span>
        </div>
      );
    };
  },
}));

// Mock API module
vi.mock("@/lib/api", () => ({
  GDSS_API_BASE_URL: "http://localhost:8787",
}));

// Mock global fetch
const mockGraphResp = {
  status: "ok",
  data: {
    summary: {
      total_nodes: 2,
      total_edges: 1,
      node_types: { function: 1, class: 1 },
      edge_relations: { calls: 1 },
    },
    nodes: [
      { id: "fn_a", name: "fn_a", type: "function", location: "a.py" },
      { id: "cls_b", name: "ClassB", type: "class", location: "b.py" },
    ],
    edges: [{ source: "fn_a", target: "cls_b", relationship: "calls" }],
  },
};

global.fetch = vi.fn().mockImplementation(async (url: string) => {
  if (url.includes("/v1/graph")) {
    return {
      ok: true,
      json: async () => mockGraphResp,
    };
  }
  return { ok: false };
}) as any;

const { default: GraphPage } = await import(
  "@/app/(dashboard)/graph/page"
);

import { RepoProvider } from "@/context/RepoContext";

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RepoProvider>{ui}</RepoProvider>
    </QueryClientProvider>
  );
}

describe("GraphPage route component", () => {
  it("renders heading and summary counts from /v1/graph API", async () => {
    renderWithClient(<GraphPage />);
    expect(screen.getByText("Semantic Graph")).toBeDefined();

    await waitFor(() => {
      expect(screen.getByText(/2 Symbols/i)).toBeDefined();
      expect(screen.getByText(/1 Connections/i)).toBeDefined();
      expect(screen.getByTestId("constellation-canvas")).toBeDefined();
    });
  });

  it("has no accessibility violations", async () => {
    const { container } = renderWithClient(<GraphPage />);
    await waitFor(() => {
      expect(screen.getByTestId("constellation-canvas")).toBeDefined();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
