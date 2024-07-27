/** @type {import('tailwindcss').Config} */
module.exports = {
  purge: ['./templates/**/*.html', './static/**/*.js'],
  darkMode: 'class', // or 'media' or 'class'
  theme: {
    extend: {
      colors: {
        primary: {
          600: '#1D4ED8', // example primary color
          700: '#1E40AF', // example primary color for dark mode
        },
      },

    },
  },
  variants: {
    extend: {},
  },
  content: [
    "./templates/**/*.html",
    "./static/src/**/*.js",
    "./node_modules/flowbite/**/*.js"
  ],
  plugins: [
    require("flowbite/plugin")
  ],
}
