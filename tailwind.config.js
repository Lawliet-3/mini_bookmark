/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./static/**/*.js"],
  theme: {
    extend: {
      colors: {
        blue: {
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E40AF',
        },
        green: {
          500: '#10B981',
          600: '#059669',
          700: '#047857',
        },
        gray: {
          100: '#F3F4F6',
          300: '#D1D5DB',
          700: '#374151',
          800: '#1F2937',
        },
      },
    },
  },
  plugins: [],
}

