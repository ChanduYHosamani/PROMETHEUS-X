/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        obsidian: '#060A13',
        navybase: '#0B1120',
        panel: '#111827',
        panelBorder: '#1E293B',
        electric: '#3B82F6',
        cyanpulse: '#06B6D4',
        ambercore: '#F59E0B',
      },
    },
  },
  plugins: [],
}
