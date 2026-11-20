/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        noche: { 950: '#070b14', 900: '#0b1220', 850: '#0f182a', 800: '#142036', 700: '#1d2c47', 600: '#2a3c5e' },
        cesped: { 900: '#0d3b24', 800: '#11492c', 700: '#155a36' },
        ofensa: '#f5b942',
        defensa: '#5ab4ff',
        ventaja: '#34d399',
        alerta: '#f87171',
      },
      fontFamily: { sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
