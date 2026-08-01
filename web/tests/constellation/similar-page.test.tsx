import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RepoProvider } from "@/context/RepoContext";

expect.extend(toHaveNoViolations);

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual<typeof import("framer-motion")>("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api", () => ({
  GDSS_API_BASE_URL: "http://localhost:8787",
}));

const mockProjectionResp = {
  status: "ok",
  data: {
    assistive: true,
    method: "pca",
    dims: 2,
    encoder: "bag",
    dim_full: 384,
    points: [
      {
        id: "ASTParser",
        name: "ASTParser",
        type: "class",
        location: "parser.py",
        x: -0.2,
        y: 0.1,
      },
      {
        id: "TransformExtractor",
        name: "TransformExtractor",
        type: "class",
        location: "extractor.py",
        x: 0.3,
        y: -0.15,
      },
    ],
  },
};

const mockSimilarResp = {
  status: "ok",
  data: {
    assistive: true,
    hits: [
      {
        id: "TransformExtractor",
        score: 0.95,
        name: "TransformExtractor",
        location: "extractor.py",
      },
    ],
  },
};

const mockSymbolsResp = {
  status: "ok",
  data: {
    symbols: [
      { id: "ASTParser", name: "ASTParser", type: "class", location: "parser.py" },
      {
        id: "TransformExtractor",
        name: "TransformExtractor",
        type: "class",
        location: "extractor.py",
      },
    ],
  },
};

beforeEach(() => {
  global.fetch = vi.fn().mockImplementation(async (url: string) => {
    if (url.includes("/v1/embeddings/projection")) {
      return { ok: true, json: async () => mockProjectionResp };
    }
    if (url.includes("/v1/similar")) {
      return { ok: true, json: async () => mockSimilarResp };
    }
    if (url.includes("/v1/symbols")) {
      return { ok: true, json: async () => mockSymbolsResp };
    }
    if (url.includes("/health") || url.includes("/v1/branches")) {
      return {
        ok: true,
        json: async () => ({
          status: "ok",
          data: { branches: ["main"], active_branch: "main", repo: "/tmp/r" },
          repo: "/tmp/r",
        }),
      };
    }
    return { ok: false };
  }) as typeof fetch;
});

const { default: SimilarPage } = await import(
  "@/app/(dashboard)/similar/page"
);

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <RepoProvider>{ui}</RepoProvider>
    </QueryClientProvider>
  );
}

describe("SimilarPage embedding-space explorer", () => {
  it("renders embedding cloud (not dependency constellation) and assistive badge", async () => {
    renderWithClient(<SimilarPage />);
    expect(screen.getByText(/Embedding Space/i)).toBeDefined();
    expect(screen.getByText(/Assistive · Probabilistic/i)).toBeDefined();
    await waitFor(() => {
      expect(screen.getByTestId("embedding-space-canvas")).toBeDefined();
    });
    expect(screen.queryByTestId("constellation-canvas")).toBeNull();
  });

  it("queries /v1/similar on search and shows ranked neighbors plus graph link", async () => {
    renderWithClient(<SimilarPage />);

    const input = screen.getByPlaceholderText(/Search symbol name/i);
    const submitBtn = screen.getByRole("button", { name: /Search/i });
    fireEvent.change(input, { target: { value: "ASTParser" } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getAllByText("TransformExtractor").length).toBeGreaterThan(0);
      expect(screen.getByText("95%")).toBeDefined();
    });
    const link = screen.getByRole("link", { name: /Open in Semantic Graph/i });
    expect(link.getAttribute("href")).toContain("/graph");
    expect(link.getAttribute("href")).toContain("ASTParser");
  });

  it("has no accessibility violations", async () => {
    const { container } = renderWithClient(<SimilarPage />);
    await waitFor(() => {
      expect(screen.getByTestId("embedding-space-canvas")).toBeDefined();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
