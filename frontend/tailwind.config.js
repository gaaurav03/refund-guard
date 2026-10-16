/** @type {import('tailwindcss').Config} */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        ink: v("ink"),
        muted: v("muted"),
        hairline: v("hairline"),
        accent: v("accent"),
        approve: v("approve"),
        partial: v("partial"),
        deny: v("deny"),
        escalate: v("escalate"),
      },
      fontFamily: {
        serif: ['"Newsreader"', "Georgia", "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: { card: "14px" },
      maxWidth: { prose: "68ch" },
    },
  },
  plugins: [],
};
