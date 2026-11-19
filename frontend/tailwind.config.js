/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: '#0b1329',
          card: '#111c44',
          border: '#1e293b',
          accent: '#2563eb',
          accentHover: '#1d4ed8',
          success: '#10b981',
          danger: '#ef4444',
          warning: '#f59e0b',
        }
      }
    },
  },
  plugins: [],
}

