export default function GraphPage() {
  return (
    <div className="flex flex-col h-full space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <h1 className="text-3xl font-bold tracking-tight text-foreground">Semantic Graph</h1>
      <p className="text-muted-foreground">
        Node dependency graph will be rendered here.
      </p>
    </div>
  );
}
