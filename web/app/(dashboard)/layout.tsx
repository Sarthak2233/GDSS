import { Navigation } from "@/components/navigation";
import { RepoRefPicker } from "@/components/repo-ref-picker";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-full w-full overflow-hidden p-3 gap-3">
      <Navigation />
      <div className="flex flex-col flex-1 h-full gap-3 min-w-0">
        <RepoRefPicker />
        <main className="flex-1 bg-surface border border-border rounded-xl p-6 shadow-md overflow-auto min-w-0 relative z-base">
          {children}
        </main>
      </div>
    </div>
  );
}
