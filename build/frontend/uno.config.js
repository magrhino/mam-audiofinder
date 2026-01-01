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
        // Atmospheric charcoal backgrounds
        'bg-primary': '#0a0a0a',         // Matte charcoal (gradient start)
        'bg-charcoal': '#0a0a0a',        // Charcoal base
        'bg-charcoal-soft': '#1a1a1a',   // Softer charcoal variant
        'bg-panel': 'rgba(36,36,36,0.7)',  // Translucent panel
        'bg-panel-hover': 'rgba(42,42,42,0.85)',

        // Maroon accent colors (oxblood maroon gradient endpoint)
        'accent-maroon': '#500000',       // Primary maroon
        'accent-maroon-dark': '#3a0000',  // Darker maroon
        'accent-maroon-light': '#6a0000', // Oxblood maroon (gradient end)

        // White/near-white text for readability
        'text-primary': '#ffffff',        // Pure white for maximum readability
        'text-secondary': '#e8e8e8',      // Near-white secondary
        'text-subtle': '#b8b8b8',         // Light gray muted text
        'text-link': '#9faed6',

        // Glass borders (subtle white semi-transparent)
        'border-default': 'rgba(255,255,255,0.08)',
        'border-focus': '#500000',
        'border-subtle': 'rgba(255,255,255,0.05)',
        'border-glass': 'rgba(255,255,255,0.12)',  // Stronger glass border

        // Input colors
        'input-bg': 'rgba(42,42,42,0.6)',
        'input-border': 'rgba(255,255,255,0.08)',
        'input-focus': '#500000',

        // Status colors
        'success': '#2d7a3e',
        'warning': '#b87333',
        'error': '#a83232',

        // Ember particle color
        'ember-glow': '#ffb366',  // Golden ember
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
        'glass': '2rem',  // Premium rounded glass effect
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
          // Existing animations
          pulse: `{
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }`,
          shimmer: `{
            0% { background-position: -468px 0; }
            100% { background-position: 468px 0; }
          }`,

          // Ember particle animations
          'drift-up': `{
            0% {
              transform: translate(0, 0) translateY(100vh);
              opacity: 0;
            }
            10% {
              opacity: 0.6;
            }
            90% {
              opacity: 0.4;
            }
            100% {
              transform: translate(var(--drift-x, 0), 0) translateY(-20vh);
              opacity: 0;
            }
          }`,
          'sway': `{
            0%, 100% { transform: translateX(0); }
            50% { transform: translateX(var(--sway-distance, 20px)); }
          }`,
          'glow-pulse': `{
            0%, 100% {
              box-shadow: 0 0 8px rgba(255, 179, 102, 0.3),
                          0 0 12px rgba(255, 85, 0, 0.2);
            }
            50% {
              box-shadow: 0 0 12px rgba(255, 179, 102, 0.5),
                          0 0 20px rgba(255, 85, 0, 0.4);
            }
          }`,
        },
      },
    },
  },

  shortcuts: {
    // Layout containers with glassmorphism
    'card': 'bg-[rgba(36,36,36,0.7)] backdrop-blur-[20px] backdrop-saturate-[200%] border border-[rgba(255,255,255,0.12)] rounded-[2rem] p-4 max-w-[1100px] shadow-[0_8px_32px_rgba(31,38,135,0.2),inset_0_4px_20px_rgba(255,255,255,0.05)]',
    'panel': 'bg-[rgba(36,36,36,0.6)] backdrop-blur-[10px] border border-[rgba(255,255,255,0.08)] rounded-md p-4',

    // Enhanced glass effects with sophisticated depth
    'glass-container': 'relative bg-[rgba(255,255,255,0.15)] backdrop-blur-[20px] backdrop-saturate-[180%] border border-[rgba(255,255,255,0.8)] rounded-[2rem] shadow-[0_8px_32px_rgba(31,38,135,0.2),inset_0_4px_20px_rgba(255,255,255,0.3)]',

    'glass-panel': 'relative bg-[rgba(255,255,255,0.15)] backdrop-blur-[20px] backdrop-saturate-[180%] border border-[rgba(255,255,255,0.8)] rounded-[2rem] shadow-[0_8px_32px_rgba(31,38,135,0.2),inset_0_4px_20px_rgba(255,255,255,0.3)] transition-all duration-300',

    'glass-panel-hover': 'hover:bg-[rgba(255,255,255,0.18)] hover:border-[rgba(106,0,0,0.6)] hover:shadow-[0_12px_40px_rgba(80,0,0,0.25),inset_0_4px_24px_rgba(255,255,255,0.4)]',

    // NEW: Glass overlay with pseudo-element shine effect (from requirements)
    // This creates the sophisticated ::after effect with inset highlights
    'glass-overlay': `after:content-[''] after:absolute after:top-0 after:left-0 after:w-full after:h-full after:bg-[rgba(255,255,255,0.1)] after:rounded-[2rem] after:shadow-[inset_-10px_-8px_0px_-11px_rgba(255,255,255,1),inset_0px_-9px_0px_-8px_rgba(255,255,255,1)] after:opacity-60 after:z-[-1] after:blur-[1px] after:brightness-[115%]`,

    // Alternating table column glass effects
    'glass-column-clear': 'bg-[rgba(255,255,255,0.15)] backdrop-blur-[10px]',  // Clearer tint for alternating columns
    'glass-column-maroon': 'bg-[rgba(106,0,0,0.2)] backdrop-blur-[10px]',      // Maroon tint for alternating columns

    // Layout utilities
    'row': 'flex gap-2 flex-wrap items-center max-md:flex-col max-md:items-stretch',

    // Table components (updated for white text)
    'table-base': 'w-full border-collapse mt-4',
    'th-base': 'p-2 border-b-2 border-[rgba(255,255,255,0.08)] text-left font-semibold text-white bg-[rgba(36,36,36,0.7)]',
    'td-base': 'p-2 border-b border-[rgba(255,255,255,0.05)] text-white',
    'tr-hover': 'hover:bg-[rgba(80,0,0,0.15)]',
    'tr-empty': 'text-center p-6 text-[#b8b8b8]',

    // Text utilities (updated to white)
    'muted': 'text-[#b8b8b8] text-[0.9rem]',
    'text-subtle': 'text-[#b8b8b8]',
    'code-inline': 'bg-[rgba(36,36,36,0.6)] px-[6px] py-[2px] rounded-sm font-mono text-[#6a0000]',
    'responsive-title': 'overflow-hidden text-ellipsis max-w-[clamp(120px,30vw,400px)]',
    'responsive-title-wrap': 'break-words overflow-hidden line-clamp-2 max-w-[clamp(150px,35vw,450px)]',
    'word-wrap-title': 'break-words hyphens-auto max-w-full',

    // Typography
    'heading-1': 'text-[1.4rem] font-semibold text-white m-0',
    'heading-3': 'text-[1.1rem] mb-2 text-white m-0',

    // Cover components
    'cover-skeleton': 'w-[60px] h-[90px] rounded-sm block',
    'cover-image': 'max-w-[60px] max-h-[90px] w-auto h-auto block rounded-sm opacity-0 transition-opacity duration-300 ease-in',
    'cover-image-loaded': 'opacity-100',
    'cover-placeholder': 'w-[60px] h-[90px] flex items-center justify-center bg-[rgba(36,36,36,0.7)] border border-[rgba(255,255,255,0.05)] rounded-sm text-[#b8b8b8] text-[0.7rem] text-center p-[4px]',

    // Focus states
    'focus-ring': 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#500000] focus-visible:outline-offset-2',

    // Body base with atmospheric gradient (charcoal → maroon)
    // Note: Horizontal padding controlled via --page-padding-x in global.css
    'body-base': 'font-sans bg-gradient-to-b from-[#0a0a0a] to-[#6a0000] text-white leading-relaxed min-h-screen m-0',

    // Button visibility shortcuts - solid backgrounds for high visibility
    'btn-primary-solid': 'bg-gradient-to-br from-[#8c2323] to-[#5a1515] text-white border border-[rgba(200,80,80,0.7)] rounded-md px-4 py-2 font-medium cursor-pointer transition-all duration-200 hover:from-[#a53232] hover:to-[#702020] hover:border-[rgba(220,100,100,0.85)] hover:-translate-y-px active:translate-y-0',

    'btn-success-solid': 'bg-[rgba(45,120,65,0.9)] text-white border border-[rgba(80,180,100,0.7)] rounded-md px-4 py-2 font-medium cursor-pointer transition-all duration-200 hover:bg-[rgba(55,140,75,0.95)] hover:border-[rgba(100,200,120,0.85)] hover:-translate-y-px active:translate-y-0',

    'btn-danger-solid': 'bg-[rgba(170,55,55,0.9)] text-white border border-[rgba(220,90,90,0.7)] rounded-md px-4 py-2 font-medium cursor-pointer transition-all duration-200 hover:bg-[rgba(190,70,70,0.95)] hover:border-[rgba(240,100,100,0.85)] hover:-translate-y-px active:translate-y-0',

    'btn-info-solid': 'bg-[rgba(70,100,160,0.9)] text-white border border-[rgba(120,160,220,0.7)] rounded-md px-4 py-2 font-medium cursor-pointer transition-all duration-200 hover:bg-[rgba(90,120,180,0.95)] hover:border-[rgba(140,180,240,0.85)] hover:-translate-y-px active:translate-y-0',

    'btn-warning-solid': 'bg-[rgba(180,120,50,0.9)] text-white border border-[rgba(220,160,80,0.7)] rounded-md px-4 py-2 font-medium cursor-pointer transition-all duration-200 hover:bg-[rgba(200,140,60,0.95)] hover:border-[rgba(240,180,100,0.85)] hover:-translate-y-px active:translate-y-0',

    'btn-secondary-solid': 'bg-[rgba(60,60,60,0.8)] text-white border border-[rgba(255,255,255,0.15)] rounded-md px-4 py-2 font-medium cursor-pointer transition-all duration-200 hover:bg-[rgba(80,80,80,0.9)] hover:border-[rgba(255,255,255,0.25)] hover:-translate-y-px active:translate-y-0',
  },

  rules: [
    // Custom animation rules
    ['animate-pulse-custom', { animation: 'pulse 1.5s ease-in-out infinite' }],
    ['animate-shimmer', {
      animation: 'shimmer 1.2s ease-in-out infinite',
      background: 'linear-gradient(90deg, rgba(36,36,36,0.7) 0%, rgba(42,42,42,0.85) 50%, rgba(36,36,36,0.7) 100%)',
      'background-size': '468px 100%',
    }],

    // Ember particle animations (slow drift: 15-20s)
    ['animate-drift-up', {
      animation: 'drift-up 18s ease-in-out infinite',
    }],
    ['animate-sway', {
      animation: 'sway 8s ease-in-out infinite',
    }],
    ['animate-glow-pulse', {
      animation: 'glow-pulse 3s ease-in-out infinite',
    }],

    // Table alignment utilities
    ['text-right', { 'text-align': 'right' }],
    ['text-center', { 'text-align': 'center' }],

    // Enhanced backdrop filter utilities (with WebKit prefixes for Safari/iOS support)
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
    ['backdrop-saturate-200', {
      'backdrop-filter': 'saturate(200%)',
      '-webkit-backdrop-filter': 'saturate(200%)',
    }],
    // Combined backdrop filters for glassmorphism
    ['backdrop-glass', {
      'backdrop-filter': 'blur(20px) saturate(180%)',
      '-webkit-backdrop-filter': 'blur(20px) saturate(180%)',
    }],
  ],

  // Safelist common dynamic classes
  safelist: [
    'animate-pulse-custom',
    'animate-shimmer',
    'animate-drift-up',
    'animate-sway',
    'animate-glow-pulse',
    'cover-image-loaded',
    'glass-panel-hover',
    'glass-overlay',
    // Button visibility shortcuts
    'btn-primary-solid',
    'btn-success-solid',
    'btn-danger-solid',
    'btn-info-solid',
    'btn-warning-solid',
    'btn-secondary-solid',
  ],
})
