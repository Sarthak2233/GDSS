#!/usr/bin/env python3
"""
GDSS frontend harness Layer F1 sensor: token fitness.

Enforces that the visual language is not improvised:
  - No raw hex colors (#rgb / #rrggbb / #rrggbbaa) outside the token files.
  - No `linear` easing used in animation (mechanical/dead; use easing tokens).
  - No raw `ms`/`s` duration literals in transition/animation contexts outside
    the token files (use `duration.*` from web/lib/motion.ts).
  - Every interactive motion component (uses whileHover/whileTap/animate with
    Framer Motion) must reference reduced-motion handling
    (useReducedMotion or prefers-reduced-motion).

Token files (exempt): web/lib/tokens.ts, web/lib/motion.ts, web/tailwind.config.ts,
web/app/globals.css (theme() references tokens).

Degrades gracefully: if web/ does not exist, SKIP. Exits non-zero on violations.
Output is agent-oriented: WHAT / WHY / FIX.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"

EXEMPT = {
    WEB / "lib" / "tokens.ts",
    WEB / "lib" / "motion.ts",
    WEB / "tailwind.config.ts",
    WEB / "app" / "globals.css",
}

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
# `linear` as an easing value, e.g. ease: "linear" or transition: { ease: "linear" }
LINEAR_EASE_RE = re.compile(r'ease\s*:\s*["\']linear["\']')
# Raw duration literals in ms/s inside transition/animation objects:
#   duration: 300  /  duration: "300ms"  /  duration: 0.25
RAW_DURATION_RE = re.compile(r"duration\s*:\s*([0-9]+(?:\.[0-9]+)?)(ms|s)?\b")
MOTION_INTERACTIVE_RE = re.compile(r"\b(whileHover|whileTap|whileFocus|whileDrag)\b")
REDUCED_MOTION_RE = re.compile(r"(useReducedMotion|prefers-reduced-motion|prefersReducedMotion)")


def is_token_file(path: Path) -> bool:
    return path in EXEMPT


def scan_file(path: Path) -> list[str]:
    if is_token_file(path):
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings: list[str] = []
    rel = path.relative_to(ROOT).as_posix()

    for m in HEX_RE.finditer(text):
        # Allow hex inside rgba()/theme() and in comments; only flag standalone hex.
        start = m.start()
        before = text[max(0, start - 8) : start]
        if "rgba(" in before or "theme(" in before:
            continue
        findings.append(
            f"WHAT: raw hex color '{m.group(0)}' in {rel}. "
            f"WHY: colors must come from the `colors` tokens in web/lib/tokens.ts; "
            f"raw hex breaks theming and the single-source-of-truth rule. "
            f"FIX: import the needed color role from '@/lib/tokens' (or use a Tailwind "
            f"theme color class) instead of a literal hex."
        )

    for _m in LINEAR_EASE_RE.finditer(text):
        findings.append(
            f"WHAT: 'linear' easing used in {rel}. "
            f"WHY: linear motion feels mechanical/dead; GDSS uses easing tokens "
            f"(easeOut/easeIn/easeInOut/spring/overshoot/anticipation). "
            f"FIX: import an easing from '@/lib/motion' and use it instead of 'linear'."
        )

    for m in RAW_DURATION_RE.finditer(text):
        # Allow if the value is a token reference like duration.primary (no number).
        # Here we matched a number literal, which is a raw duration.
        val = float(m.group(1))
        # `duration: 0` (and 0.001) is the reduced-motion "no animation" sentinel,
        # not a styled duration; exempt it.
        if val == 0 or val <= 0.001:
            continue
        findings.append(
            f"WHAT: raw duration '{m.group(0)}' in {rel}. "
            f"WHY: durations must come from the `duration` tokens in web/lib/motion.ts. "
            f"FIX: import `duration` from '@/lib/motion' and use a token "
            f"(tiny/secondary/primary/slow/page); for Framer, divide by 1000."
        )

    if MOTION_INTERACTIVE_RE.search(text) and not REDUCED_MOTION_RE.search(text):
        findings.append(
            f"WHAT: interactive motion in {rel} has no reduced-motion handling. "
            f"WHY: every animated interactive component must ship a "
            f"prefers-reduced-motion branch (accessibility gate). "
            f"FIX: call useReducedMotion() from framer-motion and gate non-essential "
            f"motion (hover/press/ambient) behind it; keep state-change transitions."
        )

    return findings


def main() -> int:
    if not WEB.is_dir():
        print("frontend/token_fitness: SKIP (web/ does not exist).")
        print("  WHY: no frontend to lint yet.")
        print("  FIX: create web/ (or run the frontend harness once it exists).")
        return 0

    exts = (".tsx", ".ts", ".css")
    files = [
        p
        for p in WEB.rglob("*")
        if p.suffix in exts and "node_modules" not in p.parts and ".next" not in p.parts
    ]

    all_findings: list[str] = []
    for f in files:
        all_findings.extend(scan_file(f))

    if not all_findings:
        print(
            "frontend/token_fitness: OK (no raw tokens, no linear easing, reduced-motion present)."
        )
        return 0

    print("frontend/token_fitness: FAIL")
    for line in all_findings:
        print("  - " + line)
    print()
    print(f"  WHY: {len(all_findings)} token-fitness violation(s) above.")
    print("  FIX: move literals into web/lib/tokens.ts or web/lib/motion.ts and reference tokens.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
