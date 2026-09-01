import { useState } from 'react'
import { NEWS_SOURCES } from '../constants/contexts'

export default function TopicsAndNews({ config, onChange }) {
  const [topicInput, setTopicInput] = useState('')
  const sources = config.news_sources || []
  const topics = config.topics || []
  const safeMode = Boolean(config.safe_mode)

  const toggleSource = (id) => {
    const next = sources.includes(id) ? sources.filter((s) => s !== id) : [...sources, id]
    onChange({ news_sources: next })
  }

  const addTopic = () => {
    const value = topicInput.trim()
    if (!value || topics.includes(value)) return
    onChange({ topics: [...topics, value] })
    setTopicInput('')
  }

  const removeTopic = (topic) => {
    onChange({ topics: topics.filter((t) => t !== topic) })
  }

  return (
    <section>
      <h3 className="font-display text-xs font-bold tracking-widest text-on-surface-variant mb-3">TOPICS &amp; NEWS</h3>

      <div className="mb-5">
        <p className="text-xs text-on-surface-variant mb-2">News sources</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(NEWS_SOURCES).map(([id, label]) => {
            const active = sources.includes(id)
            return (
              <button
                key={id}
                onClick={() => toggleSource(id)}
                className={`px-3.5 py-2 min-h-[44px] rounded-full text-xs font-display font-semibold transition-colors ${
                  active ? 'bg-primary-container text-on-primary-container' : 'bg-surface text-on-surface-variant border border-outline-variant'
                }`}
                aria-pressed={active}
              >
                {active ? '✓ ' : ''}
                {label}
              </button>
            )
          })}
        </div>
      </div>

      <div className="mb-5">
        <p className="text-xs text-on-surface-variant mb-2">Topics you're into (nudges news &amp; banter, doesn't filter hard)</p>
        <div className="flex items-center gap-2 pl-4 pr-1.5 py-1.5 rounded-full border border-outline-variant mb-2.5">
          <input
            type="text"
            value={topicInput}
            onChange={(e) => setTopicInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTopic()}
            placeholder="e.g. space, cricket, AI"
            className="flex-1 min-w-0 bg-transparent text-on-surface text-sm placeholder:text-on-surface-variant outline-none"
          />
          <button
            onClick={addTopic}
            aria-label="Add topic"
            className="w-9 h-9 shrink-0 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center text-lg font-bold"
          >
            +
          </button>
        </div>
        {topics.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {topics.map((topic) => (
              <span
                key={topic}
                className="inline-flex items-center gap-1.5 pl-3.5 pr-2 py-2 rounded-full text-xs font-display font-semibold bg-secondary-container text-on-secondary-container"
              >
                {topic}
                <button
                  onClick={() => removeTopic(topic)}
                  aria-label={`Remove ${topic}`}
                  className="w-[18px] h-[18px] rounded-full flex items-center justify-center opacity-70 hover:opacity-100"
                >
                  <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={() => onChange({ safe_mode: !safeMode })}
        className="flex items-center justify-between w-full min-h-[44px]"
        role="switch"
        aria-checked={safeMode}
      >
        <span className="flex flex-col items-start">
          <span className="text-sm font-display font-semibold text-on-surface">Safe mode</span>
          <span className="text-xs text-on-surface-variant">Keep it family-friendly</span>
        </span>
        <span className={`w-11 h-6 rounded-full relative transition-colors ${safeMode ? 'bg-primary' : 'bg-surface-container-highest'}`}>
          <span
            className={`absolute top-0.5 w-5 h-5 rounded-full transition-transform ${safeMode ? 'translate-x-[22px] bg-on-primary' : 'translate-x-0.5 bg-surface'}`}
          />
        </span>
      </button>
    </section>
  )
}
