import { Button } from "@/components/ui/button";
import { MetricCard } from "@/components/ui/metric-card";

export default function Page() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-5xl font-bold tracking-tight">GDSS</h1>
        <p className="mt-2 text-md text-textMuted">
          Geometric Distributed Software Synchronizer
        </p>
      </header>

      <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <MetricCard
          label="Trajectory length"
          value={125}
          trend={{ delta: 14, percent: 12.7, period: "Today" }}
          spark={[10, 24, 18, 40, 36, 52, 60, 75, 88, 125]}
        />
        <MetricCard
          label="Drift vs attractor"
          value={3}
          trend={{ delta: -2, percent: -40, period: "Today" }}
          spark={[8, 7, 7, 6, 5, 5, 4, 4, 3, 3]}
          tone="warning"
        />
        <MetricCard
          label="Active conflicts"
          value={1}
          trend={{ delta: 0, percent: 0, period: "Today" }}
          spark={[2, 2, 1, 1, 1, 1, 1, 1, 1, 1]}
          tone="danger"
        />
      </section>

      <section className="mt-10 flex gap-4">
        <Button intent="primary">Analyze repository</Button>
        <Button intent="secondary">View manifold</Button>
      </section>
    </main>
  );
}
