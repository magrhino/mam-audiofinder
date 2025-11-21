import { defineConfig, presetWind, presetTypography } from 'unocss'

export default defineConfig({
  presets: [
    presetWind(),
    presetTypography({
      cssExtend: {
        'code': {
          'background': 'var(--bg-panel)',
          'padding': '2px 6px',
          'border-radius': 'var(--radius-sm)',
          'font-family': "'Courier New', monospace",
          'color': 'var(--accent-maroon-light)',
        },
        'a': {
          'color': 'var(--text-link)',
          'text-decoration': 'none',
          'transition': 'color 0.2s',
        },
        'a:hover': {
          'color': 'var(--accent-maroon-light)',
          'text-decoration': 'underline',
        },
      },
    }),
  ],

  theme: {
    extend: {
      colors: {
        // Primary backgrounds
        'bg-primary': '#000000',
        'bg-panel': '#242424',
        'bg-panel-hover': '#2a2a2a',

        // Maroon accent colors
        'accent-maroon': '#500000',
        'accent-maroon-dark': '#3a0000',
        'accent-maroon-light': '#6a0000',

        // Text colors
        'text-primary': '#e8e8e8',
        'text-secondary': '#b8b8b8',
        'text-subtle': '#888888',
        'text-link': '#9faed6',

        // Border colors
        'border-default': '#3a3a3a',
        'border-focus': '#500000',
        'border-subtle': '#2a2a2a',

        // Input colors
        'input-bg': '#2a2a2a',
        'input-border': '#3a3a3a',
        'input-focus': '#500000',

        // Status colors
        'success': '#2d7a3e',
        'warning': '#b87333',
        'error': '#a83232',
      },

      spacing: {
        'xs': '0.25rem',
        'sm': '0.5rem',
        'md': '1rem',
        'lg': '1.5rem',
        'xl': '2rem',
      },

      borderRadius: {
        'sm': '6px',
        'md': '8px',
        'lg': '12px',
      },

      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ["'Courier New'", 'monospace'],
      },

      lineHeight: {
        'relaxed': '1.6',
      },

      animation: {
        keyframes: {
          pulse: `{
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }`,
          shimmer: `{
            0% { background-position: -468px 0; }
            100% { background-position: 468px 0; }
          }`,
        },
      },
    },
  },

  shortcuts: {
    // Layout containers
    'card': 'bg-[rgba(36,36,36,0.7)] backdrop-blur-[10px] border border-[var(--border-default)] rounded-lg p-4 max-w-[1100px] shadow-[0_4px_6px_rgba(0,0,0,0.3)]',
    'panel': 'bg-[var(--bg-panel)] border border-[var(--border-default)] rounded-md p-4',

    // Glass effects
    'glass-container': 'bg-[rgba(26,26,26,0.4)] backdrop-blur-[20px] backdrop-saturate-[180%] border border-[rgba(80,0,0,0.3)] rounded-lg shadow-[0_4px_16px_rgba(0,0,0,0.3),inset_0_1px_0_rgba(255,255,255,0.05)]',
    'glass-panel': 'bg-[rgba(36,36,36,0.7)] backdrop-blur-[10px] border border-[rgba(255,255,255,0.08)] rounded-lg shadow-[0_4px_12px_rgba(0,0,0,0.3)] transition-all duration-300',
    'glass-panel-hover': 'hover:bg-[rgba(36,36,36,0.85)] hover:border-[rgba(80,0,0,0.4)] hover:shadow-[0_6px_16px_rgba(80,0,0,0.2),inset_0_1px_0_rgba(255,255,255,0.1)]',

    // Layout utilities
    'row': 'flex gap-2 flex-wrap items-center max-md:flex-col max-md:items-stretch',

    // Table components
    'table-base': 'w-full border-collapse mt-4',
    'th-base': 'p-2 border-b-2 border-[var(--border-default)] text-left font-semibold text-[var(--text-secondary)] bg-[var(--bg-panel)]',
    'td-base': 'p-2 border-b border-[var(--border-subtle)] text-[var(--text-primary)]',
    'tr-hover': 'hover:bg-[rgba(42,42,42,0.3)]',
    'tr-empty': 'text-center p-6 text-[var(--text-subtle)]',

    // Text utilities
    'muted': 'text-[var(--text-subtle)] text-[0.9rem]',
    'text-subtle': 'text-[var(--text-subtle)]',
    'code-inline': 'bg-[var(--bg-panel)] px-[6px] py-[2px] rounded-sm font-mono text-[var(--accent-maroon-light)]',

    // Typography
    'heading-1': 'text-[1.4rem] font-semibold text-[var(--text-primary)] m-0',
    'heading-3': 'text-[1.1rem] mb-2 text-[var(--text-primary)] m-0',

    // Cover components
    'cover-skeleton': 'w-[60px] h-[90px] rounded-sm block',
    'cover-image': 'max-w-[60px] max-h-[90px] w-auto h-auto block rounded-sm opacity-0 transition-opacity duration-300 ease-in',
    'cover-image-loaded': 'opacity-100',
    'cover-placeholder': 'w-[60px] h-[90px] flex items-center justify-center bg-[var(--bg-panel)] border border-[var(--border-subtle)] rounded-sm text-[var(--text-subtle)] text-[0.7rem] text-center p-[4px]',

    // Focus states
    'focus-ring': 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--accent-maroon)] focus-visible:outline-offset-2',

    // Body base
    'body-base': 'font-sans bg-black text-[var(--text-primary)] leading-relaxed p-8 max-md:p-4 min-h-screen m-0',
  },

  rules: [
    // Custom animation rules
    ['animate-pulse-custom', { animation: 'pulse 1.5s ease-in-out infinite' }],
    ['animate-shimmer', {
      animation: 'shimmer 1.2s ease-in-out infinite',
      background: 'linear-gradient(90deg, var(--bg-panel) 0%, var(--bg-panel-hover) 50%, var(--bg-panel) 100%)',
      'background-size': '468px 100%',
    }],

    // Table alignment utilities
    ['text-right', { 'text-align': 'right' }],
    ['text-center', { 'text-align': 'center' }],

    // Backdrop filter utilities (for better browser support)
    ['backdrop-blur-10', {
      'backdrop-filter': 'blur(10px)',
      '-webkit-backdrop-filter': 'blur(10px)',
    }],
    ['backdrop-blur-20', {
      'backdrop-filter': 'blur(20px)',
      '-webkit-backdrop-filter': 'blur(20px)',
    }],
    ['backdrop-saturate-180', {
      'backdrop-filter': 'saturate(180%)',
      '-webkit-backdrop-filter': 'saturate(180%)',
    }],
  ],

  // Safelist common dynamic classes
  safelist: [
    'animate-pulse-custom',
    'animate-shimmer',
    'cover-image-loaded',
    'glass-panel-hover',
  ],
})
