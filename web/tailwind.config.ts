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
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        // Body sans — referenced via the default `font-sans` utility
        // since we want Geist to be the document default.
        sans: ['"Geist"', "ui-sans-serif", "system-ui", "sans-serif"],
        // `font-serif` → editorial display.
        serif: ['"Fraunces"', "ui-serif", "Georgia", "serif"],
        // `font-mono` → ids, hashes, code.
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        // Alias `font-display` for explicit display use.
        display: ['"Fraunces"', "ui-serif", "Georgia", "serif"],
      },
      boxShadow: {
        // "Photo-on-paper" lift for cards. Soft, warm-tinted, not
        // material-design crisp.
        paper: "0 1px 2px hsl(30 20% 20% / 0.06), 0 8px 24px hsl(30 20% 20% / 0.05)",
        "paper-hover":
          "0 2px 4px hsl(30 20% 20% / 0.08), 0 12px 32px hsl(30 20% 20% / 0.08)",
      },
    },
  },
  plugins: [],
} satisfies Config;

export default config;
