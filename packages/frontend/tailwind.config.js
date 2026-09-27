/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#0f110a',
          900: '#14160f',
          800: '#1c1f15',
          700: '#282c1e',
          600: '#333728',
          500: '#4a4f38',
        },
        copper: {
          DEFAULT: '#c98a3e',
          dim: '#a87232',
          glow: 'rgba(201, 138, 62, 0.4)',
        },
        brass: {
          DEFAULT: '#b8963a',
          dim: '#9c7d2f',
          glow: 'rgba(184, 150, 58, 0.4)',
        },
        fix: {
          DEFAULT: '#6b8e5a',
          bright: '#8fd476',
          glow: 'rgba(107, 142, 90, 0.4)',
        },
        teal: {
          DEFAULT: '#1f6f6b',
          soft: '#4db8b1',
          glow: 'rgba(31, 111, 107, 0.4)',
        },
        brass: {
          DEFAULT: '#b8963a',
          dim: '#9c7d2f',
          glow: 'rgba(184, 150, 58, 0.4)',
        },
        lamp: {
          DEFAULT: '#f5e6c8',
          dim: '#e8d4a8',
        },
        fail: {
          DEFAULT: '#c0392b',
          soft: '#e87a6a',
          glow: 'rgba(192, 57, 43, 0.4)',
        },
        warn: {
          DEFAULT: '#c98a3e',
        },
        fix: {
          DEFAULT: '#6b8e5a',
          bright: '#8fd476',
          glow: 'rgba(107, 142, 90, 0.4)',
        },
      },
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}