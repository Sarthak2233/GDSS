"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Sparkles, Binary } from "lucide-react";
import { Button } from "@/components/ui/button";
import { duration, easing } from "@/lib/motion";

export function HeroPanel() {
  const reduced = useReducedMotion();
  const [isHovered, setIsHovered] = useState(false);
  const [isFocused, setIsFocused] = useState(false);

  const isVisible = Boolean(reduced || isHovered || isFocused);

  const sec = (ms: number) => ms / 1000;

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
      className="relative z-content max-w-3xl w-full mx-auto p-2"
    >
      <motion.div
        initial={false}
        animate={{
          opacity: isVisible ? 1 : 0,
          scale: reduced ? 1 : isVisible ? 1 : 0.95,
          y: reduced ? 0 : isVisible ? 0 : 10,
        }}
        transition={{
          duration: sec(duration.slow),
          ease: isVisible ? easing.easeOut : easing.easeIn,
        }}
        className={`p-6 sm:p-10 rounded-2xl bg-surfaceGlass border border-border/80 shadow-2xl text-center overflow-hidden transition-all duration-300 ${
          isVisible ? "backdrop-blur-xl pointer-events-auto" : "backdrop-blur-none pointer-events-auto"
        }`}
        data-testid="hero-panel"
      >
        {/* Background glow accent */}
        {!reduced && isVisible && (
          <div className="absolute -top-24 -left-24 w-72 h-72 bg-accent/15 rounded-full blur-3xl pointer-events-none" />
        )}

        {/* Header: Badge */}
        <div className="flex flex-col items-center gap-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent/10 border border-accent/20 text-xs font-semibold text-accent tracking-wide uppercase">
            <Sparkles className="h-3.5 w-3.5" />
            Continuous Geometric Synchronizer
          </div>
        </div>

        {/* Body: Title & Subtitle */}
        <div className="mt-4 space-y-4">
          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-text leading-tight">
            The Semantic Intelligence Layer{" "}
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-accent via-merge to-trajectory">
              Above Git
            </span>
          </h1>
          <p className="text-sm sm:text-lg text-textMuted max-w-2xl mx-auto leading-relaxed font-normal">
            Software development as a continuous geometric-semantic dynamical system. Predict branch drift, conflict energy, and trajectory convergence before merge.
          </p>
        </div>

        {/* Mathematical Notation Box */}
        <div className="my-6 inline-flex flex-col items-center gap-2 px-4 py-2.5 rounded-xl bg-surfaceElevated/80 border border-border text-xs sm:text-sm font-mono text-textSubtle select-none shadow-inner max-w-lg mx-auto">
          <div className="flex items-center gap-3">
            <Binary className="h-4 w-4 text-accent shrink-0" />
            <span>
              <strong className="text-accent font-semibold">Conflict Tensor (roadmap):</strong>{" "}
              <span className="text-text font-medium">Ω_ij = [T_i, T_j] ≠ 0</span>
            </span>
          </div>
          <p className="text-[11px] text-textMuted font-sans leading-relaxed text-center">
            Today&apos;s UI shows phase 1–3 drift + a{" "}
            <strong className="text-warning">flat heuristic</strong> conflict
            score — not the full geometric Ω. See{" "}
            <span className="font-mono text-textSubtle">docs/MANIFOLD_TENSOR_GUIDE.md</span>.
          </p>
        </div>

        {/* Action / CTA */}
        <div className="mt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/dashboard">
            <Button intent="primary" size="lg" className="w-full sm:w-auto px-8 group shadow-lg shadow-accent/20">
              <span>Explore Dashboard</span>
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
          </Link>
          <Link href="/graph">
            <Button intent="secondary" size="lg" className="w-full sm:w-auto">
              <span>View Semantic Graph</span>
            </Button>
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
