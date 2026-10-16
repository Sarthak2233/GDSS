import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { IntegrityRibbon } from "../../components/dashboard/integrity-ribbon";
import { axe } from "jest-axe";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("IntegrityRibbon component", () => {
  it("renders repo integrity badge, repo path, reference branch, and observer beacon", () => {
    render(
      <IntegrityRibbon
        repoPath="/home/sarakb/projects/GDSS"
        referenceBranch="main"
        isHealthy={true}
      />
    );

    expect(screen.getByText("REPO INTEGRITY VERIFIED")).toBeInTheDocument();
    expect(screen.getByText("/home/sarakb/projects/GDSS")).toBeInTheDocument();
    expect(screen.getByText("main")).toBeInTheDocument();
    expect(screen.getByText("Git Observer active")).toBeInTheDocument();
    expect(screen.getByTestId("integrity-ribbon")).toBeInTheDocument();
  });

  it("renders warning badge when isHealthy is false", () => {
    render(
      <IntegrityRibbon
        repoPath="/home/sarakb/projects/GDSS"
        referenceBranch="main"
        isHealthy={false}
      />
    );
    expect(screen.getByText("INTEGRITY DEGRADED")).toBeInTheDocument();
  });

  it("renders loading skeleton when isLoading is true", () => {
    render(
      <IntegrityRibbon
        repoPath="."
        referenceBranch="main"
        isLoading={true}
      />
    );
    expect(
      screen.getByTestId("integrity-ribbon-skeleton")
    ).toBeInTheDocument();
  });

  it("renders error state when error is provided", () => {
    render(
      <IntegrityRibbon
        repoPath="."
        referenceBranch="main"
        error="Failed to verify repo integrity"
      />
    );
    expect(
      screen.getByText("Failed to verify repo integrity")
    ).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <IntegrityRibbon
        repoPath="/home/sarakb/projects/GDSS"
        referenceBranch="main"
        isHealthy={true}
      />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
