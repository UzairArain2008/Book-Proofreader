import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1B2430",
        slate: {
          850: "#1E2937",
        },
        paper: "#F7F8FA",
        accent: {
          DEFAULT: "#2A5C55",
          light: "#3D7A70",
          dark: "#1C433D",
        },
        signal: {
          amber: "#B8752A",
          red: "#B3432E",
          green: "#3D7A5C",
        },
      },
      fontFamily: {
        serif: ["Source Serif 4", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(27, 36, 48, 0.06), 0 1px 8px rgba(27, 36, 48, 0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
