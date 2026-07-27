/**
 * GDSS frontend design tokens - the single source of truth.
 *
 * The frontend harness lints against these tokens (see
 * harness/sensors/frontend/token_fitness). Do NOT introduce raw px/ms/hex
 * values or arbitrary Tailwind spacing outside this file and motion.ts.
 *
 * Spacing communicates hierarchy before color. Use the scale, do not invent it.
 */

/** 4px base spacing scale. Index = number of 4px units. */
export const spacing = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  8: 32,
  10: 40,
  12: 48,
  16: 64,
  20: 80,
  24: 96,
} as const;

export type SpacingToken = keyof typeof spacing;

/** Radii follow the same 4px rhythm. */
export const radius = {
  none: 0,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  "2xl": 24,
  full: 9999,
} as const;

/**
 * Color tokens as semantic roles, not raw hex. Components reference roles;
 * themes swap the underlying values. Raw hex lives ONLY here.
 */
export const colors = {
  // Surfaces
  bg: "#0b0d12",
  surface: "#11141b",
  surfaceElevated: "#171b24",
  surfaceGlass: "rgba(23, 27, 36, 0.6)",
  // Text
  text: "#e6e9ef",
  textMuted: "#9aa3b2",
  textSubtle: "#6b7384",
  // Borders / hairlines
  border: "#222838",
  borderStrong: "#2f374a",
  // Semantic accents
  accent: "#7c5cff",
  accentMuted: "#5b4ad1",
  success: "#3ddc97",
  warning: "#ffb454",
  danger: "#ff6b6b",
  // GDSS manifold concepts (see .cursor/rules/frontend/11-data-visualization)
  node: "#7c5cff",
  edge: "#3a4256",
  conflict: "#ff6b6b",
  drift: "#ffb454",
  trajectory: "#3ddc97",
  merge: "#5cc8ff",
} as const;

/** Typography scale - modular, 1.125 ratio. */
export const fontSize = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  "2xl": 24,
  "3xl": 30,
  "4xl": 36,
  "5xl": 48,
} as const;

export const fontWeight = {
  regular: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const;

export const lineHeight = {
  tight: 1.15,
  snug: 1.3,
  normal: 1.5,
  relaxed: 1.7,
} as const;

/** Z-index hierarchy - lower numbers never cover higher. */
export const z = {
  base: 0,
  content: 10,
  sticky: 20,
  overlay: 30,
  modal: 40,
  toast: 50,
  tooltip: 60,
} as const;
