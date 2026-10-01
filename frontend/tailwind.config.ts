import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "rgb(var(--ink) / <alpha-value>)",
        sage: "rgb(var(--sage) / <alpha-value>)",
        sand: "rgb(var(--sand) / <alpha-value>)",
      },
    },
  },
  plugins: [],
};

export default config;
