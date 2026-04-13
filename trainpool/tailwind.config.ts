import type { Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Forest green (primary) + warm ivory (background) + signal orange (accent)
        ink: {
          50: "#f7f7f5",
          100: "#efede8",
          200: "#d9d6cc",
          300: "#b8b2a0",
          400: "#8a836f",
          500: "#5f5947",
          600: "#3f3a2c",
          700: "#2a261b",
          800: "#1a1810",
          900: "#0f0e09",
        },
        forest: {
          50: "#f0f6f1",
          100: "#dbeadd",
          200: "#b7d5bd",
          300: "#8cbb96",
          400: "#5e9c6c",
          500: "#3d7d4c",
          600: "#2a5f39",
          700: "#1f4b2e",
          800: "#193b25",
          900: "#12291a",
        },
        signal: {
          50: "#fff4ec",
          100: "#ffe4cc",
          200: "#ffc08a",
          300: "#ff9647",
          400: "#fb7118",
          500: "#e85a0a",
          600: "#c04709",
          700: "#943509",
          800: "#6b2507",
          900: "#461806",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Fraunces", "ui-serif", "Georgia", "serif"],
      },
      maxWidth: {
        prose: "65ch",
      },
    },
  },
  plugins: [],
} satisfies Config;
