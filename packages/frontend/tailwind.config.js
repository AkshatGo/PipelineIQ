export default {
  content: [
    './index.html',
    './*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './data/**/*.{ts,tsx}',
    './utils/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: '#12140F',
          900: '#171912',
          800: '#1F221A',
          700: '#2B2E22',
        },
        line: '#33362A',
        muted: '#A6A08C',
        paper: '#EDE6D6',
        fail: { DEFAULT: '#B3452F', soft: '#DA7A62' },
        copper: '#C98A3E',
        warn: '#C98A3E',
        fix: '#7C9A6B',
        teal: { DEFAULT: '#2F6E6A', soft: '#7DB8B1' },
        brass: '#9C7A3C',
        lamp: '#F3E6C8',
      },
      fontFamily: {
        sans: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        sm: '3px',
        DEFAULT: '4px',
        md: '6px',
        lg: '8px',
      },
      backgroundImage: {
        signal: 'linear-gradient(95deg, #B3452F 0%, #C98A3E 55%, #7C9A6B 100%)',
      },
      keyframes: {
        'marquee-left': {
          from: { transform: 'translateX(0)' },
          to: { transform: 'translateX(-50%)' },
        },
        'marquee-right': {
          from: { transform: 'translateX(-50%)' },
          to: { transform: 'translateX(0)' },
        },
        caret: {
          '0%, 49%': { opacity: '1' },
          '50%, 100%': { opacity: '0' },
        },
      },
      animation: {
        'marquee-left': 'marquee-left 70s linear infinite',
        'marquee-right': 'marquee-right 70s linear infinite',
        caret: 'caret 1s steps(1) infinite',
      },
    },
  },
  plugins: [],
};