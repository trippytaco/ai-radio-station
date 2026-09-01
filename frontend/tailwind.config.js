/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: ['class'],
  theme: {
    extend: {
      colors: {
        primary: 'var(--m3-primary)',
        'on-primary': 'var(--m3-on-primary)',
        'primary-container': 'var(--m3-primary-container)',
        'on-primary-container': 'var(--m3-on-primary-container)',

        'secondary-container': 'var(--m3-secondary-container)',
        'on-secondary-container': 'var(--m3-on-secondary-container)',

        tertiary: 'var(--m3-tertiary)',
        'tertiary-container': 'var(--m3-tertiary-container)',
        'on-tertiary-container': 'var(--m3-on-tertiary-container)',

        news: 'var(--m3-news)',

        error: 'var(--m3-error)',
        'on-error': 'var(--m3-on-error)',
        'error-container': 'var(--m3-error-container)',
        'on-error-container': 'var(--m3-on-error-container)',

        surface: 'var(--m3-surface)',
        'surface-container-lowest': 'var(--m3-surface-container-lowest)',
        'surface-container-low': 'var(--m3-surface-container-low)',
        'surface-container': 'var(--m3-surface-container)',
        'surface-container-high': 'var(--m3-surface-container-high)',
        'surface-container-highest': 'var(--m3-surface-container-highest)',
        'on-surface': 'var(--m3-on-surface)',
        'on-surface-variant': 'var(--m3-on-surface-variant)',

        outline: 'var(--m3-outline)',
        'outline-variant': 'var(--m3-outline-variant)',
        scrim: 'var(--m3-scrim)',
        // Alpha baked directly into the oklch() value (not a Tailwind
        // opacity modifier - bg-x/NN doesn't work on these custom tokens
        // since they're full oklch() strings, not channel-only values).
        'scrim-overlay': 'var(--m3-scrim-overlay)',
        'surface-overlay': 'var(--m3-surface-overlay)',

        // Fixed distinguishing colors for the mix sliders - not part of
        // the dynamic-color role system (which uses primary/secondary/
        // tertiary), so they stay stable regardless of the seed hues.
        music: 'var(--m3-music)',
        ads: 'var(--m3-ads)'
      },
      fontFamily: {
        display: ['Roboto Flex', 'Roboto', 'system-ui', 'sans-serif'],
        body: ['Roboto Flex', 'Roboto', 'system-ui', 'sans-serif']
      },
      borderRadius: {
        xs: '8px',
        sm: '12px',
        DEFAULT: '16px',
        lg: '20px',
        xl: '28px',
        full: '9999px'
      }
    }
  },
  plugins: []
}
