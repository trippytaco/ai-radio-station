// Each context preset drives: slider weights, the hero banner slot, and
// the show name/tagline shown in the overlay. Banner art is a placeholder
// CSS gradient per slot (grayscale photography as specified would replace
// the `banner` gradient with a real background-image) - see
// Hero.jsx BANNER_STYLES.
export const CONTEXTS = {
  workout: {
    id: 'workout',
    icon: '🏃',
    label: 'Workout',
    desc: 'Music + motivation',
    showName: 'Running Show',
    tagline: 'Keep the pace, keep the energy.',
    weights: { music_weight: 0.75, news_weight: 0.05, ad_weight: 0.2 }
  },
  commute: {
    id: 'commute',
    icon: '🚗',
    label: 'Commute',
    desc: 'Music + news + banter',
    showName: 'Morning Drive',
    tagline: "What's happening, on your way in.",
    weights: { music_weight: 0.5, news_weight: 0.3, ad_weight: 0.1 }
  },
  chill: {
    id: 'chill',
    icon: '☕',
    label: 'Chill',
    desc: 'Laid-back vibes',
    showName: 'Arvo Session',
    tagline: 'Nothing to prove, nowhere to be.',
    weights: { music_weight: 0.85, news_weight: 0.05, ad_weight: 0.1 }
  },
  custom: {
    id: 'custom',
    icon: '⚙️',
    label: 'Custom',
    desc: 'Full control',
    showName: 'Your Mix',
    tagline: 'Exactly how you like it.',
    weights: { music_weight: 0.5, news_weight: 0.3, ad_weight: 0.1 }
  }
}

export const CONTEXT_ORDER = ['workout', 'commute', 'chill', 'custom']

export const HOSTS = {
  alex: { id: 'alex', name: 'Alex', desc: 'Sassy & witty' },
  jordan: { id: 'jordan', name: 'Jordan', desc: 'Smooth & sardonic' }
}

export const NEWS_SOURCES = {
  bbc: 'BBC',
  guardian: 'The Guardian',
  cnn: 'CNN'
}
