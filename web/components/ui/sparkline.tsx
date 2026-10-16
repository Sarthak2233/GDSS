"use client";

import { motion, useReducedMotion } from "framer-motion";
import { duration, easing } from "@/lib/motion";

/**
 * Sparkline - lightweight SVG trend line for MetricCard.
 * Draws in over `duration.slow` with `easeOut`; the latest point pulses.
 * Reduced motion: render the final path statically (no draw-in / pulse).
 */
export function Sparkline({
  data,
  width = 120,
  height = 36,
  stroke = "currentColor",
}: {
  data: number[];
  width?: number;
  height?: number;
  stroke?: string;
}) {
  const reduceMotion = useReducedMotion();

  if (data.length < 2) {
    return <svg width={width} height={height} aria-hidden />;
  }

  const max = Math.max(...data);
  const min = Math.min(...data);
  const span = max - min || 1;
  const stepX = width / (data.length - 1);
  const points = data.map((v, i) => {
    const x = i * stepX;
    const y = height - ((v - min) / span) * (height - 4) - 2;
    return [x, y] as const;
  });
  const d = points
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");
  const last = points[points.length - 1];

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden
      role="presentation"
    >
      <motion.path
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={reduceMotion ? undefined : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={
          reduceMotion
            ? { duration: 0 }
            : { duration: duration.slow / 1000, ease: easing.easeOut }
        }
      />
      {!reduceMotion && (
        <motion.circle
          cx={last[0]}
          cy={last[1]}
          r={2.5}
          fill={stroke}
          initial={{ scale: 0.6, opacity: 0.4 }}
          animate={{ scale: [0.8, 1.4, 0.8], opacity: [0.6, 1, 0.6] }}
          transition={{
            duration: duration.slow / 1000,
            repeat: Infinity,
            ease: easing.easeInOut,
          }}
        />
      )}
      {reduceMotion && <circle cx={last[0]} cy={last[1]} r={2.5} fill={stroke} />}
    </svg>
  );
}
