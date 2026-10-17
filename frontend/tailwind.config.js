/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        midnight: '#050816',
        slateBlue: '#111827',
        accent: '#3b82f6',
        accentSoft: '#60a5fa',
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(59,130,246,0.25), 0 16px 40px rgba(2,8,23,0.45)',
      },
    },
  },
  plugins: [],
};
