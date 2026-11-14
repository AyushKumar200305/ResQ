/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        resq: {
          bg: "#f8fafc",
          surface: "#ffffff",
          card: "#ffffff",
          cardHover: "#fbfcfe",
          border: "#e2e8f0",
          borderLight: "#f1f5f9",
          navy: {
            DEFAULT: "#0f172a",
            light: "#1e293b",
            muted: "#334155",
          },
          accent: {
            blue: "#2563eb",
            blueLight: "#eff6ff",
            teal: "#0d9488",
            tealLight: "#f0fdfa",
            red: "#dc2626",
            redLight: "#fef2f2",
            redDark: "#991b1b",
            amber: "#d97706",
            amberLight: "#fffbeb",
            amberDark: "#b45309",
            green: "#059669",
            greenLight: "#ecfdf5",
            greenDark: "#047857",
            cyan: "#0284c7",
          },
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "Roboto", "sans-serif"],
        mono: ["JetBrains Mono", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        card: "0 1px 3px 0 rgb(0 0 0 / 0.07), 0 1px 2px -1px rgb(0 0 0 / 0.05)",
        cardHover: "0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.05)",
        modal: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
      },
    },
  },
  plugins: [],
};
