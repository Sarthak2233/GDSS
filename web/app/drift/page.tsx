export default function DriftPage() {
  return (
    <div className="flex flex-col h-full space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <h1 className="text-3xl font-bold tracking-tight text-foreground">Drift Monitor</h1>
      <p className="text-muted-foreground">
        Per-branch drift magnitude against the reference attractor will be displayed here.
      </p>
    </div>
  );
}
