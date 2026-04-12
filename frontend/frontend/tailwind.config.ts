import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          0: "var(--bg-0)",
          1: "var(--bg-1)",
          2: "var(--bg-2)",
          3: "var(--bg-3)"
        },
        border: {
          0: "var(--border-0)",
          1: "var(--border-1)"
        },
        text: {
          0: "var(--text-0)",
          1: "var(--text-1)",
          2: "var(--text-2)",
          3: "var(--text-3)"
        },
        blue: {
          DEFAULT: "var(--blue)",
          dim: "var(--blue-dim)",
          border: "var(--blue-border)",
          text: "var(--blue-text)"
        },
        green: {
          DEFAULT: "var(--green)",
          dim: "var(--green-dim)",
          border: "var(--green-border)"
        },
        amber: {
          DEFAULT: "var(--amber)",
          dim: "var(--amber-dim)",
          border: "var(--amber-border)"
        },
        purple: {
          DEFAULT: "var(--purple)",
          dim: "var(--purple-dim)",
          border: "var(--purple-border)"
        },
        red: {
          DEFAULT: "var(--red)",
          dim: "var(--red-dim)",
          border: "var(--red-border)"
        },
        orange: {
          DEFAULT: "var(--orange)",
          dim: "var(--orange-dim)",
          border: "var(--orange-border)"
        }
      },
      fontFamily: {
        mono: ["var(--font-ibm-plex-mono)"],
        sans: ["var(--font-ibm-plex-sans)"]
      }
    }
  },
  plugins: [tailwindcssAnimate]
};

export default config;
