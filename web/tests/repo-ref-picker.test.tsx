import { render, screen, waitFor, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RepoRefPicker } from "@/components/repo-ref-picker";
import { axe } from "jest-axe";
import { RepoProvider } from "@/context/RepoContext";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetcher: vi.fn(async (url: string) => {
      if (url === "/health") {
        return { version: "1.0", status: "ok", repo: "/tmp/fixture-repo" };
      }
      if (url.includes("/v1/branches")) {
        return {
          status: "ok",
          data: {
            branches: ["main", "feature"],
            active_branch: "feature",
            repo: "/tmp/fixture-repo",
          },
        };
      }
      throw new Error(`unexpected url ${url}`);
    }),
  };
});

function wrap(ui: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <RepoProvider>{ui}</RepoProvider>
    </QueryClientProvider>
  );
}

describe("RepoRefPicker component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows read-only repo and ref dropdown from /v1/branches", async () => {
    render(wrap(<RepoRefPicker />));

    await waitFor(() => {
      expect(screen.getByTestId("repo-readonly")).toHaveTextContent(
        "/tmp/fixture-repo"
      );
    });

    const select = screen.getByTestId("ref-select") as HTMLSelectElement;
    expect(select.tagName).toBe("SELECT");
    await waitFor(() => {
      expect(select.options.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("has no accessibility violations", async () => {
    const { container } = render(wrap(<RepoRefPicker />));
    await waitFor(() => {
      expect(screen.getByTestId("repo-readonly")).toBeInTheDocument();
    });
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("allows toggling branch scope filter", async () => {
    render(wrap(<RepoRefPicker />));

    await waitFor(() => {
      expect(screen.getByTestId("branch-scope-btn")).toBeInTheDocument();
    });

    const scopeBtn = screen.getByTestId("branch-scope-btn");
    expect(scopeBtn).toHaveTextContent(/All branches/i);

    // Click to open filter
    act(() => {
      fireEvent.click(scopeBtn);
    });

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    // Toggle feature branch checkbox
    const featureCheckbox = screen.getByRole("checkbox") as HTMLInputElement;
    expect(featureCheckbox).toBeInTheDocument();
    act(() => {
      fireEvent.click(featureCheckbox);
    });

    await waitFor(() => {
      expect(scopeBtn).toHaveTextContent("1 selected");
    });
  });
});

