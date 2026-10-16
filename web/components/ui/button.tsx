"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { motion, useReducedMotion, type HTMLMotionProps } from "framer-motion";
import { Loader2, Check } from "lucide-react";
import { forwardRef, type ReactNode } from "react";
import { duration, easing, type InteractionState } from "@/lib/motion";
import { cn } from "@/lib/utils";

/**
 * GDSS Button - canonical 8-state interaction machine.
 * States: idle -> hover -> focused -> pressed -> loading -> success -> failure
 *         -> disabled.
 * All durations/easings come from web/lib/motion.ts (no raw ms/linear).
 */

const button = cva(
  [
    "inline-flex items-center justify-center gap-2 rounded-md font-medium",
    "transition-colors select-none",
    "disabled:cursor-not-allowed",
  ],
  {
    variants: {
      intent: {
        primary: "bg-accent text-white hover:bg-accentMuted",
        secondary:
          "bg-surface text-text border border-border hover:border-borderStrong",
        ghost: "bg-transparent text-textMuted hover:text-text",
        danger: "bg-danger text-white hover:brightness-110",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-md",
        lg: "h-12 px-6 text-lg",
      },
    },
    defaultVariants: { intent: "primary", size: "md" },
  },
);

type ButtonProps = Omit<HTMLMotionProps<"button">, "children"> &
  VariantProps<typeof button> & {
    children?: ReactNode;
    state?: Partial<Record<InteractionState, boolean>>;
    /** Transient success affordance (overshoot tick), auto-clears via parent. */
    successLabel?: string;
  };

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    { intent, size, className, children, state, successLabel, ...props },
    ref,
  ) {
    const reduceMotion = useReducedMotion();
    const isLoading = state?.loading ?? false;
    const isSuccess = state?.success ?? false;
    const isDisabled = props.disabled ?? state?.disabled ?? false;

    // Level 1 hover + Level 2 pressed micro-interactions (skipped on reduced motion).
    const motionProps = reduceMotion
      ? {}
      : {
          whileHover: isDisabled || isLoading ? undefined : { y: -1 },
          whileTap: isDisabled || isLoading ? undefined : { scale: 0.97 },
          transition: { duration: duration.primary / 1000, ease: easing.easeOut },
        };

    return (
      <motion.button
        ref={ref}
        className={cn(button({ intent, size }), className)}
        aria-disabled={isDisabled || undefined}
        aria-busy={isLoading || undefined}
        {...motionProps}
        {...props}
        disabled={isDisabled}
      >
        {isLoading && (
          <Loader2
            className="h-4 w-4 animate-spin"
            aria-hidden
            data-testid="button-loading"
          />
        )}
        {isSuccess && !isLoading && (
          <motion.span
            initial={reduceMotion ? false : { scale: 0.4, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{
              duration: duration.secondary / 1000,
              ease: easing.overshoot,
            }}
            aria-hidden
            data-testid="button-success"
          >
            <Check className="h-4 w-4" />
          </motion.span>
        )}
        <span>{isSuccess && successLabel ? successLabel : children}</span>
      </motion.button>
    );
  },
);
