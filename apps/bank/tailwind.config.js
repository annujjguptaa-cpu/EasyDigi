/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
    '../../packages/ui/src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        paper: 'var(--bg-paper)',
        surface: 'var(--bg-surface)',
        ink: {
          DEFAULT: 'var(--ink-primary)',
          muted: 'var(--ink-muted)',
        },
        hairline: 'var(--border-hairline)',
        status: {
          verified: 'var(--status-verified)',
          flagged: 'var(--status-flagged)',
          missing: 'var(--status-missing)',
          error: 'var(--status-error)',
          success: 'var(--status-success)',
        },
      },
      fontFamily: {
        serif: ['var(--font-serif)', 'Fraunces', 'Source Serif 4', 'Georgia', 'serif'],
        sans: ['var(--font-sans)', 'Inter', 'sans-serif'],
        mono: ['var(--font-mono)', 'JetBrains Mono', 'monospace'],
        devanagari: ['var(--font-devanagari)', 'Noto Sans Devanagari', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '2px',
        sm: '2px',
        md: '3px',
        lg: '4px',
      },
      spacing: {
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        6: '24px',
        8: '32px',
        12: '48px',
      },
      borderWidth: {
        DEFAULT: '1px',
        hairline: '1px',
      },
    },
  },
  plugins: [],
};
