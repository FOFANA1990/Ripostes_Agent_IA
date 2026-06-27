/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1A1A2E",
        accent: "#E94560",
        brand: "#3A86FF",
      },
    },
  },
  plugins: [],
};
