/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        gold: {
          DEFAULT: '#F59E0B',
          dim:     '#92400E',
          light:   '#FCD34D',
        },
        surface: {
          DEFAULT: '#18181B',
          2:       '#27272A',
          3:       '#3F3F46',
        },
        bg: '#09090B',
      },
      fontFamily: {
        sans: ["'Segoe UI'", 'system-ui', 'sans-serif'],
        mono: ["'Courier New'", 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'fade-in':    'fadeIn 0.3s ease-out',
        'slide-up':   'slideUp 0.3s ease-out',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { opacity: '0', transform: 'translateY(12px)' },
                   '100%': { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
