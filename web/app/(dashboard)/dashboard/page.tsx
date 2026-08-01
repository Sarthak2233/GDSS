import React from "react";
import type { Metadata } from "next";
import { DashboardGrid } from "@/components/dashboard/dashboard-grid";

export const metadata: Metadata = {
  title: "Status Dashboard | GDSS",
  description:
    "Real-time semantic trajectory, drift versus attractor, and conflict prediction metrics.",
};

export default function DashboardPage() {
  return (
    <div className="flex flex-col h-full w-full justify-between gap-6">
      <div className="flex flex-col space-y-1">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Status Dashboard
        </h1>
        <p className="text-muted-foreground">
          Live semantic trajectory, drift versus attractor, and conflict prediction metrics.
        </p>
      </div>
      <DashboardGrid />
    </div>
  );
}
