import type { Config } from "tailwindcss";
import { spacing, radius, colors, fontSize, fontWeight, lineHeight, z } from "./lib/tokens";
import { duration, easing } from "./lib/motion";

/**
 * Tailwind is wired to the SAME tokens in lib/tokens.ts and lib/motion.ts so
 * the harness can lint against a single source of truth. Arbitrary spacing or
 * raw durations outside these scales are flagged by token_fitness.
 */
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      spacing: Object.fromEntries(
        Object.entries(spacing).map(([k, v]) => [k, `${v}px`]),
      ),
      borderRadius: Object.fromEntries(
        Object.entries(radius).map(([k, v]) => [k, `${v}px`]),
      ),
      colors,
      fontSize: Object.fromEntries(
        Object.entries(fontSize).map(([k, v]) => [
          k,
          [`${v}px`, { lineHeight: String(lineHeight.snug) }],
        ]),
      ),
      fontWeight: Object.fromEntries(
        Object.entries(fontWeight).map(([k, v]) => [k, String(v)]),
      ),
      zIndex: Object.fromEntries(
        Object.entries(z).map(([k, v]) => [k, String(v)]),
      ),
      transitionDuration: Object.fromEntries(
        Object.entries(duration)
          .filter(([, v]) => v !== Infinity)
          .map(([k, v]) => [k, `${v}ms`]),
      ),
      transitionTimingFunction: Object.fromEntries(
        Object.entries(easing).map(([k, v]) => [k, `cubic-bezier(${v.join(",")})`]),
      ),
      keyframes: {
        breathe: {
          "0%, 100%": { transform: "scale(1)", opacity: "0.85" },
          "50%": { transform: "scale(1.06)", opacity: "1" },
        },
        pulseEdge: {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "0.9" },
        },
        glowConflict: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(255,107,107,0.0)" },
          "50%": { boxShadow: "0 0 16px 2px rgba(255,107,107,0.45)" },
        },
      },
      animation: {
        breathe: "breathe 4s ease-in-out infinite",
        "pulse-edge": "pulseEdge 3s ease-in-out infinite",
        "glow-conflict": "glowConflict 2.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
