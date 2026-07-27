/** @type {import('eslint').Linter.Config} */
const config = {
  root: true,
  extends: ["next/core-web-vitals", "plugin:jsx-a11y/recommended"],
  plugins: ["jsx-a11y"],
  rules: {
    // Accessibility is a hard gate, not a warning.
    "jsx-a11y/anchor-is-valid": "error",
    "jsx-a11y/no-noninteractive-tabindex": "error",
    "jsx-a11y/no-static-element-interactions": "warn",
  },
  ignorePatterns: ["node_modules", ".next", "dist"],
};

module.exports = config;
