export default function DashboardPage() {
  return (
    <div className="flex flex-col h-full space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <h1 className="text-3xl font-bold tracking-tight text-foreground">Status Dashboard</h1>
      <p className="text-muted-foreground">
        Trajectory, drift vs attractor, and conflicts metrics will be displayed here.
      </p>
    </div>
  );
}
