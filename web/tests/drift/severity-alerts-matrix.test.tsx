import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { axe } from "jest-axe";
import {
  SeverityAlertsMatrix,
  DriftAlertItem,
} from "../../components/drift/severity-alerts-matrix";

vi.mock("framer-motion", async () => {
  const actual = await vi.importActual("framer-motion");
  return {
    ...actual,
    useReducedMotion: () => true,
  };
});

describe("SeverityAlertsMatrix component", () => {
  const sampleAlerts: DriftAlertItem[] = [
    {
      branch: "feature/auth-refactor",
      severity: "CRITICAL",
      message: "Alert severity CRITICAL",
      magnitude: 0.85,
      affected: [
        { id: "gdss/auth/service.py::AuthService", name: "AuthService" },
        { id: "gdss/auth/service.py::login", name: "login" },
      ],
    },
    {
      branch: "feature/graph-ui",
      severity: "HIGH",
      message: "Alert severity HIGH",
      magnitude: 0.45,
      affected: [{ id: "web/components/constellation.tsx::Canvas", name: "Canvas" }],
    },
    {
      branch: "feature/docs",
      severity: "LOW",
      message: "Alert severity LOW",
      magnitude: 0.1,
      affected: [],
    },
  ];

  it("renders severity bucket filter pills and displays matching alert items", () => {
    render(<SeverityAlertsMatrix alerts={sampleAlerts} />);

    expect(screen.getByText("Severity-Bucketed Alerts Console")).toBeDefined();
    expect(screen.getAllByText("ALL").length).toBeGreaterThan(0);
    expect(screen.getAllByText("CRITICAL").length).toBeGreaterThan(0);
    expect(screen.getAllByText("HIGH").length).toBeGreaterThan(0);
    expect(screen.getAllByText("LOW").length).toBeGreaterThan(0);

    expect(screen.getByText("Alert severity CRITICAL")).toBeDefined();
    expect(screen.getByText("Alert severity HIGH")).toBeDefined();
    expect(screen.getByText("Alert severity LOW")).toBeDefined();

    expect(screen.getByText("AuthService")).toBeDefined();
    expect(screen.getByText("login")).toBeDefined();
  });

  it("renders Geometric Remediation Guide footer for alerts", () => {
    render(<SeverityAlertsMatrix alerts={sampleAlerts} />);

    expect(
      screen.getByText(/Non-commutative transformation/i)
    ).toBeDefined();
  });

  it("filters alerts when a severity bucket pill is clicked", () => {
    render(<SeverityAlertsMatrix alerts={sampleAlerts} />);

    const criticalBtn = screen.getByRole("button", { name: /CRITICAL/i });
    fireEvent.click(criticalBtn);

    expect(screen.getByText("Alert severity CRITICAL")).toBeDefined();
    expect(screen.queryByText("Alert severity HIGH")).toBeNull();
    expect(screen.queryByText("Alert severity LOW")).toBeNull();
  });

  it("calls onSelectSymbol when an affected symbol chip is clicked", () => {
    const handleSelectSymbol = vi.fn();
    render(
      <SeverityAlertsMatrix
        alerts={sampleAlerts}
        onSelectSymbol={handleSelectSymbol}
      />
    );

    const symbolChip = screen.getByRole("button", { name: /AuthService/i });
    fireEvent.click(symbolChip);

    expect(handleSelectSymbol).toHaveBeenCalledWith(
      "gdss/auth/service.py::AuthService"
    );
  });

  it("renders Attractor Equilibrium Shield when there are no alerts", () => {
    render(<SeverityAlertsMatrix alerts={[]} />);
    expect(screen.getByText(/Commutative Equilibrium/i)).toBeDefined();
    expect(screen.getByText(/stable around the attractor/i)).toBeDefined();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<SeverityAlertsMatrix alerts={sampleAlerts} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
