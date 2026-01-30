/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0f766e', // teal style to keep UI consistent
        accent: '#0891b2'
      }
    }
  },
  plugins: []
};

