import { Logo } from "@/components/ui/logo";
import { ManifoldCanvas } from "@/components/landing/manifold-canvas";
import { HeroPanel } from "@/components/landing/hero-panel";
import { StatPills } from "@/components/landing/stat-pills";
import { ScrollSections } from "@/components/landing/scroll-sections";
import { OrbitalDock } from "@/components/landing/orbital-dock";

export default function Home() {
  return (
    <main className="relative min-h-screen w-full overflow-x-hidden overflow-y-auto bg-bg text-text font-sans pb-28">
      {/* Top-Left Floating GDSS Brand Logo Box */}
      <div className="fixed top-6 left-6 z-sticky">
        <div className="bg-surfaceGlass backdrop-blur-xl border border-border/80 rounded-xl px-4 py-2.5 shadow-xl flex items-center justify-center">
          <Logo />
        </div>
      </div>

      {/* Background Interactive Semantic Manifold Canvas */}
      <ManifoldCanvas />

      {/* Main Hero Viewport */}
      <div className="relative z-content min-h-screen flex flex-col items-center justify-between pt-24 pb-16 px-4 pointer-events-none">
        <div className="my-auto w-full pointer-events-auto">
          <HeroPanel />
        </div>

        {/* Metric Cards moved down right above the Orbital Dock */}
        <div className="w-full max-w-4xl mx-auto mb-2 pointer-events-auto">
          <StatPills />
        </div>
      </div>

      {/* Below the fold content */}
      <ScrollSections />

      {/* Unique Orbital Dock Navigation */}
      <OrbitalDock />
    </main>
  );
}
