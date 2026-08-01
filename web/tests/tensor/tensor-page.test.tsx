import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { axe } from "jest-axe";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RepoProvider } from "../../context/RepoContext";
import TensorPage from "../../app/(dashboard)/tensor/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => "/tensor",
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

const tensorPayload = {
  status: "ok",
  data: {
    reference: "main",
    form: "flat",
    branches: ["feature", "main"],
    entries: [
      {
        i: "feature",
        j: "main",
        omega: 0.42,
        reasons: ["same_file", "interference=1.00"],
      },
      {
        i: "feature",
        j: "feature",
        omega: 0.8,
        reasons: ["drift_self_energy"],
      },
    ],
    merge_risk: 0.97,
    commutativity: [
      {
        a: "rename_function",
        b: "delete_function",
        class: "interfere",
      },
      {
        a: "modify_function",
        b: "modify_function",
        class: "commute",
      },
    ],
  },
  warnings: [],
};

vi.mock("../../lib/api", async () => {
  const actual = await vi.importActual("../../lib/api");
  return {
    ...actual,
    fetcher: vi.fn(async (url: string) => {
      if (url === "/health") {
        return { version: "1.0", status: "ok", repo: "/tmp/repo" };
      }
      if (url.includes("/v1/branches")) {
        return {
          status: "ok",
          data: {
            branches: ["main", "feature"],
            active_branch: "main",
            repo: "/tmp/repo",
          },
        };
      }
      if (url.includes("/v1/tensor")) {
        return tensorPayload;
      }
      throw new Error(`unexpected url ${url}`);
    }),
  };
});

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <RepoProvider>
        <TensorPage />
      </RepoProvider>
    </QueryClientProvider>
  );
}

describe("TensorPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads flat Omega heatmap, merge risk, and commutativity", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("omega-heatmap")).toBeInTheDocument();
    });
    expect(screen.getByTestId("merge-risk-card")).toBeInTheDocument();
    expect(screen.getByTestId("commutativity-table")).toBeInTheDocument();
    expect(screen.getByText(/Conflict Tensor/i)).toBeInTheDocument();
    expect(screen.getAllByText(/never auto-merge/i).length).toBeGreaterThan(0);
  });

  it("has no accessibility violations", async () => {
    const { container } = renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("omega-heatmap")).toBeInTheDocument();
    });
    expect(await axe(container)).toHaveNoViolations();
  });
});
