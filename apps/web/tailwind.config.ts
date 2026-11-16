import type { Config } from "tailwindcss";
import typography from "@tailwindcss/typography";

/*
 * Semantic roles alias the DesignKit values mapped in src/tokens.css.
 * Keep values in tokens.css; only role names belong here.
 */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--color-surface-canvas)",
        surface: "var(--color-surface-default)",
        wash: "var(--color-surface-subtle)",
        ink: {
          DEFAULT: "var(--color-text-primary)",
          muted: "var(--color-text-muted)",
          faint: "var(--color-text-subtle)",
        },
        line: {
          DEFAULT: "var(--color-border-default)",
          strong: "var(--color-border-hover)",
        },
        accent: {
          DEFAULT: "var(--color-accent-default)",
          muted: "var(--color-accent-muted)",
          strong: "var(--color-accent-strong)",
          soft: "var(--color-accent-soft)",
          "soft-hover": "var(--color-accent-soft-hover)",
          border: "var(--color-accent-border)",
          ink: "var(--color-accent-ink)",
          deep: "var(--color-accent-deep)",
        },
        link: "var(--color-link)",
        focus: "var(--color-focus-ring)",
        action: {
          DEFAULT: "var(--color-action-primary)",
          hover: "var(--color-action-primary-hover)",
          text: "var(--color-action-primary-text)",
          border: "var(--color-action-primary-border)",
        },
        "control-thumb": "var(--color-control-thumb)",
        success: {
          DEFAULT: "var(--color-feedback-success)",
          soft: "var(--color-feedback-success-soft)",
          border: "var(--color-feedback-success-border)",
        },
        warning: {
          DEFAULT: "var(--color-feedback-warning)",
          soft: "var(--color-feedback-warning-soft)",
          border: "var(--color-feedback-warning-border)",
        },
        danger: {
          DEFAULT: "var(--color-feedback-danger)",
          soft: "var(--color-feedback-danger-soft)",
          border: "var(--color-feedback-danger-border)",
        },
        info: {
          DEFAULT: "var(--color-feedback-info)",
          soft: "var(--color-feedback-info-soft)",
        },
        band: {
          success: "var(--color-band-success)",
          warning: "var(--color-band-warning)",
          danger: "var(--color-band-danger)",
        },
      },
      fontFamily: {
        display: "var(--font-display)",
        sans: "var(--font-body)",
        mono: "var(--font-mono)",
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem", letterSpacing: "0.04em" }],
      },
      borderRadius: {
        none: "0",
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius-md)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        full: "9999px",
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
        overlay: "var(--shadow-overlay)",
      },
      keyframes: {
        "fade-up": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          from: { backgroundPosition: "200% 0" },
          to: { backgroundPosition: "-200% 0" },
        },
      },
      animation: {
        "fade-up": "fade-up var(--motion-standard)",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
  plugins: [typography],
} satisfies Config;
