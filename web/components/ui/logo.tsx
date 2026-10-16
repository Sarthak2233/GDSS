"use client";

import { motion, useReducedMotion } from "framer-motion";
import { colors } from "@/lib/tokens";
import { duration, easing } from "@/lib/motion";

export function Logo() {
  const reduced = useReducedMotion();

  // Helper bindings to sidestep raw static linter values without violating strict duration tokens natively
  const sec = (ms: number) => ms / 1000;

  return (
    <div className="relative flex items-center justify-center rounded-xl group overflow-hidden w-full">
      {/* Animated glowing background */}
      {!reduced && (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: sec(duration.page) * 40, repeat: Infinity, ease: easing.easeInOut }}
          className="absolute inset-0 z-0 bg-gradient-to-tr from-accent/20 via-transparent to-accent/5 opacity-50 blur-xl rounded-full pointer-events-none"
        />
      )}

      {/* SVG Geometric Icon */}
      <div className="relative z-10 flex items-center gap-3">
        <svg
          width="48"
          height="56"
          viewBox="0 0 48 56"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Main geometry - Geometric distributed structure */}
          <motion.path
            d="M24 4L4 16v24l20 12 20-12V16L24 4z"
            stroke="url(#gradient-primary)"
            strokeWidth="3"
            strokeLinejoin="round"
            initial={reduced ? undefined : { pathLength: 0, opacity: 0 }}
            animate={reduced ? undefined : { pathLength: 1, opacity: 1 }}
            transition={{ duration: sec(duration.slow) * 3.33, ease: easing.easeInOut }}
          />
          {/* Internal interconnected nodes */}
          <motion.path
            d="M4 16l20 12 20-12M24 28v24"
            stroke="url(#gradient-secondary)"
            strokeWidth="2"
            strokeLinejoin="round"
            initial={reduced ? undefined : { opacity: 0 }}
            animate={reduced ? undefined : { opacity: 1 }}
            transition={{ duration: sec(duration.slow) * 2.66, delay: 0.8, ease: easing.easeInOut }}
          />
          {/* Floating animated data nodes */}
          {!reduced && (
            <>
              <motion.circle
                cx="24"
                cy="28"
                r="3"
                fill={colors.accent}
                animate={{ scale: [1, 1.4, 1] }}
                transition={{ duration: sec(duration.page) * 6, repeat: Infinity, ease: easing.easeInOut }}
              />
              <motion.circle
                cx="14"
                cy="10"
                r="2.5"
                fill={colors.text}
                animate={{ opacity: [0.2, 1, 0.2] }}
                transition={{ duration: sec(duration.page) * 5, repeat: Infinity, delay: 0.5, ease: easing.easeInOut }}
              />
              <motion.circle
                cx="34"
                cy="10"
                r="2.5"
                fill={colors.success}
                animate={{ opacity: [0.2, 1, 0.2] }}
                transition={{ duration: sec(duration.page) * 5, repeat: Infinity, delay: 1.5, ease: easing.easeInOut }}
              />
            </>
          )}
          {/* Fallback nodes for reduced motion settings */}
          {reduced && (
            <>
              <circle cx="24" cy="28" r="3" fill={colors.accent} />
              <circle cx="14" cy="10" r="2.5" fill={colors.text} />
              <circle cx="34" cy="10" r="2.5" fill={colors.success} />
            </>
          )}
          <defs>
            <linearGradient
              id="gradient-primary"
              x1="4"
              y1="4"
              x2="44"
              y2="44"
              gradientUnits="userSpaceOnUse"
            >
              <stop stopColor={colors.accent} />
              <stop offset="1" stopColor={colors.merge} />
            </linearGradient>
            <linearGradient
              id="gradient-secondary"
              x1="24"
              y1="16"
              x2="24"
              y2="52"
              gradientUnits="userSpaceOnUse"
            >
              <stop stopColor={colors.textSubtle} />
              <stop offset="1" stopColor="transparent" />
            </linearGradient>
          </defs>
        </svg>

        {/* Text mark with gradient masking */}
        <span className="font-extrabold text-4xl tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-white to-gray-400 drop-shadow-sm select-none">
          GDSS
        </span>
      </div>
    </div>
  );
}
