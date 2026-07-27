/**
 * GDSS motion tokens - the single source of truth for animation.
 *
 * Motion is not decoration. Motion explains. People notice movement before
 * color before text, so motion guides attention and clarifies state change.
 *
 * Rules enforced by harness/sensors/frontend/token_fitness:
 *   - Never use `linear` easing for UI motion (it feels mechanical/dead).
 *   - Never use raw ms durations outside this file; import from `duration`.
 *   - Every interactive component must ship a `prefers-reduced-motion` branch.
 *
 * See .cursor/skills/motion-design/motion.md for the full animation hierarchy.
 */

/** Animation duration scale (ms). */
export const duration = {
  /** 100ms - tiny feedback: ripple, press snap, toggle tick. */
  tiny: 100,
  /** 180ms - secondary actions: icon morph, label swap, subtle hover. */
  secondary: 180,
  /** 250ms - primary actions: button hover lift, card elevation, state change. */
  primary: 250,
  /** 450ms - slow / appear-disappear: modal in, toast, list stagger tail. */
  slow: 450,
  /** 500ms - page transitions, shared-layout morphs. */
  page: 500,
} as const;

export type DurationToken = keyof typeof duration;

/**
 * Easing curves. Prefer `easeOut` for things entering the screen (decelerate),
 * `easeIn` for things leaving, `easeInOut` for state transitions between two
 * visible states. Use `spring` for physics-feeling interactions (drag, toggle).
 */
export const easing = {
  easeOut: [0.16, 1, 0.3, 1] as [number, number, number, number],
  easeIn: [0.7, 0, 0.84, 0] as [number, number, number, number],
  easeInOut: [0.65, 0, 0.35, 1] as [number, number, number, number],
  /** Slight overshoot for delightful micro-interactions. */
  overshoot: [0.34, 1.56, 0.64, 1] as [number, number, number, number],
  /** Anticipation: pull back before the main motion (Disney principle). */
  anticipation: [0.5, -0.2, 0.4, 1.2] as [number, number, number, number],
} as const;

export type EasingToken = keyof typeof easing;

/** Framer Motion spring presets for physics-based interactions. */
export const spring = {
  /** Snappy, low bounce - toggles, switches, snaps. */
  snap: { type: "spring", stiffness: 500, damping: 30, mass: 1 } as const,
  /** Gentle, natural - drag release, card lift. */
  gentle: { type: "spring", stiffness: 200, damping: 26, mass: 1 } as const,
  /** Bouncy - playful confirmations, success states. */
  bouncy: { type: "spring", stiffness: 350, damping: 14, mass: 1 } as const,
} as const;

/**
 * The 8-state interaction machine. Every interactive component must reason
 * about these states explicitly rather than ad-hoc `if loading: spinner`.
 *
 *   Idle -> Hover -> Focused -> Pressed -> Loading -> Success -> Failure -> Disabled
 *
 * States are not all linear; they form a graph. But every component must
 * *define* its visual response for each reachable state.
 */
export const interactionStates = [
  "idle",
  "hover",
  "focused",
  "pressed",
  "loading",
  "success",
  "failure",
  "disabled",
] as const;

export type InteractionState = (typeof interactionStates)[number];

/**
 * Animation hierarchy (Level 0 -> Level 10). Every animated element must know
 * which level it belongs to; do not animate randomly. Higher levels are rarer
 * and more expensive (attention + performance).
 *
 *   0  Nothing moves
 *   1  Hover
 *   2  Pressed
 *   3  Focus
 *   4  Appear
 *   5  Disappear
 *   6  State change
 *   7  Layout transition
 *   8  Page transition
 *   9  Background animation
 *  10  Physics simulation
 */
export const animationLevel = {
  none: 0,
  hover: 1,
  pressed: 2,
  focus: 3,
  appear: 4,
  disappear: 5,
  stateChange: 6,
  layout: 7,
  page: 8,
  background: 9,
  physics: 10,
} as const;

export type AnimationLevel = keyof typeof animationLevel;

/** Motion hierarchy by role - primary actions get the most time. */
export const motionHierarchy = {
  primaryAction: duration.primary,
  secondary: duration.secondary,
  tinyFeedback: duration.tiny,
  pageTransition: duration.page,
  background: Infinity, // ambient loops; never block perception
} as const;

/** Shared Framer Motion variants for staggered component reveal (anatomy). */
export const revealStagger = {
  container: {
    hidden: {},
    show: {
      transition: { staggerChildren: duration.secondary / 1000, delayChildren: 0.04 },
    },
  },
  // Children reveal in anatomy order: container -> header -> body -> actions -> footer.
  item: {
    hidden: { opacity: 0, y: 8 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: duration.primary / 1000, ease: easing.easeOut },
    },
  },
} as const;
