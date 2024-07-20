/** @type {import('tailwindcss').Config} */
module.exports = {
  purge: ['./templates/**/*.html', './static/**/*.js'],
  darkMode: false, // or 'media' or 'class'
  theme: {
    extend: {},
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
