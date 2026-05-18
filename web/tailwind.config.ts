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
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        // V2 (SESSION 178) — consolidated to Geist for display +
        // body. Fraunces (V1 editorial serif) retired with the
        // brand pivot. JetBrains Mono unchanged.
        sans: ['"Geist"', "ui-sans-serif", "system-ui", "sans-serif"],
        // `font-serif` kept as an alias for Geist so existing
        // class names don't break; V2 has no serif primitive.
        serif: ['"Geist"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        display: ['"Geist"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        // V2 dark-tuned multi-layer shadows. The `paper-*` names
        // are preserved (existing components reference them) but
        // re-pointed at the V2 token CSS vars. New code should
        // prefer `shadow`, `shadow-md`, etc. — the Tailwind
        // defaults — which now resolve to V2 values via the
        // `--shadow*` custom properties in tokens.css.
        paper: "var(--shadow-sm)",
        "paper-hover": "var(--shadow)",
        gold: "var(--shadow-gold)",
      },
    },
  },
  plugins: [],
} satisfies Config;

export default config;
