import { useState } from 'react'
import { NEWS_SOURCES } from '../constants/contexts'

export default function TopicsAndNews({ config, onChange }) {
  const [topicInput, setTopicInput] = useState('')
  const sources = config.news_sources || []
  const topics = config.topics || []

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
      <h3 className="font-display text-xs font-bold tracking-widest text-muted mb-3">TOPICS &amp; NEWS</h3>

      <div className="mb-4">
        <p className="text-xs text-muted mb-2">News sources</p>
        <div className="flex flex-wrap gap-2">
          {Object.entries(NEWS_SOURCES).map(([id, label]) => {
            const active = sources.includes(id)
            return (
              <button
                key={id}
                onClick={() => toggleSource(id)}
                className={`px-3 py-2 min-h-[44px] border-2 border-line text-xs font-display font-semibold transition-colors ${
                  active ? 'bg-accent text-white' : 'bg-bg hover:bg-surface'
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

      <div className="mb-4">
        <p className="text-xs text-muted mb-2">Topics you're into (nudges news &amp; banter, doesn't filter hard)</p>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={topicInput}
            onChange={(e) => setTopicInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && addTopic()}
            placeholder="e.g. space, cricket, AI"
            className="flex-1 px-3 py-2 min-h-[44px] border-2 border-line bg-bg text-fg text-sm"
          />
          <button
            onClick={addTopic}
            className="px-4 min-h-[44px] border-2 border-line bg-bg hover:bg-surface font-display text-xs font-bold"
          >
            ADD
          </button>
        </div>
        {topics.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {topics.map((topic) => (
              <span
                key={topic}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 border-2 border-line text-xs font-display"
              >
                {topic}
                <button
                  onClick={() => removeTopic(topic)}
                  aria-label={`Remove ${topic}`}
                  className="text-muted hover:text-accent"
                >
                  ✕
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      <label className="flex items-center gap-3 min-h-[44px] cursor-pointer">
        <input
          type="checkbox"
          checked={Boolean(config.safe_mode)}
          onChange={(e) => onChange({ safe_mode: e.target.checked })}
          className="w-5 h-5 border-2 border-line accent-current"
        />
        <span className="text-sm font-display font-semibold">Safe mode</span>
        <span className="text-xs text-muted">— keep it family-friendly</span>
      </label>
    </section>
  )
}
