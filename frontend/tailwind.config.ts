import type { Config } from 'tailwindcss'

export default {
  content: [
    './app/**/*.{vue,js,ts,jsx,tsx}',
    './components/**/*.{vue,js,ts,jsx,tsx}',
    './layouts/**/*.{vue,js,ts,jsx,tsx}',
    './pages/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        cream: '#fffefb',
        'cream-alt': '#fffdf9',
        'ds-black': '#201515',
        'ds-orange': '#ff4f00',
        charcoal: '#36342e',
        'ds-gray': '#939084',
        sand: '#c5c0b1',
        'sand-light': '#eceae3',
        'sand-mid': '#b5b2aa',
      },
      borderRadius: {
        tight: '3px',
        standard: '4px',
        content: '5px',
        comfortable: '8px',
        social: '14px',
        pill: '20px',
      },
      fontFamily: {
        inter: ['Inter', 'Helvetica', 'Arial', 'sans-serif'],
        degular: ['Degular Display', 'Inter', 'Helvetica', 'Arial', 'sans-serif'],
        alpina: ['GT Alpina', 'Georgia', 'Times New Roman', 'serif'],
      },
    },
  },
  plugins: [],
} satisfies Config
