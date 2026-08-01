import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { GlobalHealthDialCard } from "../../components/dashboard/global-health-dial-card";
import { axe } from "jest-axe";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("GlobalHealthDialCard component", () => {
  it("renders global alignment score, remote sync details, and radar visualizer", () => {
    render(
      <GlobalHealthDialCard
        alignmentScore={94}
        remoteSync={{ label: "origin/main", ahead: 0, behind: 0 }}
      />
    );

    expect(screen.getByText("Remote Sync & Drift")).toBeInTheDocument();
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("origin/main")).toBeInTheDocument();
    expect(screen.getByText("Synced with remote")).toBeInTheDocument();
    expect(
      screen.getByText("From /v1/status remote_sync + /v1/drift")
    ).toBeInTheDocument();
    expect(screen.getByTestId("global-health-dial-card")).toBeInTheDocument();
  });

  it("renders ahead/behind counts when remote branch diverges", () => {
    render(
      <GlobalHealthDialCard
        alignmentScore={88}
        remoteSync={{ label: "origin/main", ahead: 2, behind: 1 }}
      />
    );
    expect(screen.getByText("2 ahead, 1 behind")).toBeInTheDocument();
  });

  it("renders loading skeleton when isLoading is true", () => {
    render(<GlobalHealthDialCard isLoading={true} />);
    expect(
      screen.getByTestId("global-health-dial-card-skeleton")
    ).toBeInTheDocument();
  });

  it("renders error message when error is provided", () => {
    render(
      <GlobalHealthDialCard error="Failed to scan global alignment" />
    );
    expect(
      screen.getByText("Failed to scan global alignment")
    ).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <GlobalHealthDialCard
        alignmentScore={94}
        remoteSync={{ label: "origin/main", ahead: 0, behind: 0 }}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
