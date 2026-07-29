// Minimal ESLint setup — ENG-013. Scope is intentionally narrow: catch dead
// imports/variables (the frontend's equivalent of the backend's `ruff
// --select F401,F811,F841` sweep), not enforce a full style guide. See
// docs/engineering/FIX_LOG.md "ENG-013" for why this scope was chosen.
import globals from "globals";

export default [
  {
    files: ["src/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "module",
      parserOptions: { ecmaFeatures: { jsx: true } },
      globals: {
        ...globals.browser,
        React: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { args: "none", varsIgnorePattern: "^_" }],
      "no-undef": "off",
    },
  },
];
