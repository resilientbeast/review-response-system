/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#050C1A',
        surface: '#0C1528',
        border: '#1A2845',
        borderBright: '#2A3E65',
        textPrimary: '#D8E4F0',
        textSub: '#5A7090',
        textMuted: '#2A3D58',
        amber: '#F59E0B',
        amberFaint: '#2D1800',
        emerald: '#10B981',
        emeraldFaint: '#041A10',
        rose: '#F43F5E',
        roseFaint: '#200810',
        blue: '#3B82F6',
        violet: '#8B5CF6',
        cyan: '#06B6D4',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['system-ui', '-apple-system', 'sans-serif'],
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      },
      animation: {
        fadeIn: 'fadeIn 0.3s ease-out',
      }
    },
  },
  plugins: [],
}
