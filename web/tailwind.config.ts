import type { Config } from "tailwindcss";

// Standard shadcn/ui-compatible Tailwind config. Theme tokens are
// CSS variables defined in src/styles/globals.css so shadcn's
// generated components reference them without ceremony.
const config = {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
          muted: "hsl(var(--accent-muted))",
          bright: "hsl(var(--accent-bright))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        // V3 (SESSION 209) — raw brand colors for the editorial
        // dark-luxe palette. These map to the `--color-*` vars
        // in tokens.css under `[data-brand="v3"]` so `text-gold`,
        // `bg-ink`, `border-luxe`, etc. work as expected. The V2
        // semantic tokens above continue to drive shadcn primitives.
        ink: "var(--color-ink)",
        night: "var(--color-night)",
        midnight: "var(--color-midnight)",
        deep: "var(--color-deep)",
        steel: "var(--color-steel)",
        fog: "var(--color-fog)",
        mist: "var(--color-mist)",
        bone: "var(--color-bone)",
        cream: "var(--color-cream)",
        gold: {
          DEFAULT: "var(--color-gold)",
          bright: "var(--color-gold-bright)",
          deep: "var(--color-gold-deep)",
        },
        ember: "var(--color-ember)",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        // V3 (SESSION 209) — Bodoni Moda display + DM Sans body +
        // JetBrains Mono mono. The CSS-var indirection lets
        // `data-brand="v2"` roll back to Geist by overriding
        // `--font-*` in the V2 token block.
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"],
        serif: ["var(--font-display)", "Georgia", "serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        display: ["var(--font-display)", "Georgia", "serif"],
      },
      boxShadow: {
        paper: "var(--shadow-sm)",
        "paper-hover": "var(--shadow)",
        gold: "var(--shadow-gold)",
        luxe: "var(--shadow-luxe)",
      },
      // V3 keyframes registered with semantic animation names.
      // Keyframe definitions live in globals.css as @keyframes
      // blocks (Tailwind reads from the global stylesheet at
      // animation-run time; this block names the utility classes).
      keyframes: {
        rise: {
          from: { opacity: "0", transform: "translateY(28px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        orbit: {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        shimmer: {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
        ticker: {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(-50%)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "0.4" },
          "50%": { opacity: "0.9" },
        },
      },
      animation: {
        rise: "rise 1.2s cubic-bezier(0.2, 0.65, 0.2, 1) both",
        orbit: "orbit 24s linear infinite",
        "orbit-slow": "orbit 42s linear infinite",
        "orbit-fast": "orbit 14s linear infinite",
        shimmer: "shimmer 4s ease-in-out infinite",
        ticker: "ticker 60s linear infinite",
        "pulse-soft": "pulse-soft 3s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;

export default config;
