export default function Loading() {
  return (
    <div className="flex w-full h-full min-h-[400px] animate-pulse space-x-6 p-6 rounded-xl border border-border bg-card/50">
      <div className="flex-1 max-w-md space-y-6">
        <div className="h-8 bg-muted rounded w-3/4"></div>
        <div className="h-4 bg-muted rounded w-1/2"></div>
        <div className="h-48 bg-muted rounded w-full mt-8"></div>
        <div className="h-32 bg-muted rounded w-full"></div>
      </div>
      <div className="flex-[2] space-y-6 flex flex-col">
        <div className="h-16 bg-muted rounded w-full mb-4"></div>
        <div className="flex-1 bg-muted rounded w-full min-h-[200px]"></div>
      </div>
    </div>
  );
}
