import React, { useState, useEffect } from 'react';
import { Play, Pause, Settings, Volume2, Radio, Clock } from 'lucide-react';

const RadioDashboard = () => {
  const [config, setConfig] = useState({
    music_weight: 0.5,
    news_weight: 0.3,
    ad_weight: 0.1,
    host_personality: 'alex',
    news_sources: ['bbc', 'guardian'],
    context: 'commute',
    active_hosts: ['alex']
  });

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentSegment, setCurrentSegment] = useState(null);
  const [schedule, setSchedule] = useState({});
  const [showSchedule, setShowSchedule] = useState(false);

  // Use whatever host the dashboard itself was loaded from (LAN IP,
  // Tailscale hostname, localhost, ...) rather than hardcoding localhost,
  // which only works when viewing the dashboard on the same machine the
  // API runs on.
  const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;

  // Fetch current config on load
  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/config`);
      const data = await response.json();
      setConfig(data);
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  };

  const updateConfig = async (newConfig) => {
    try {
      await fetch(`${API_BASE}/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newConfig)
      });
      setConfig(newConfig);
    } catch (error) {
      console.error('Error updating config:', error);
    }
  };

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
    if (!isPlaying) {
      startStream();
    }
  };

  const startStream = async () => {
    try {
      const response = await fetch(`${API_BASE}/stream/session?duration_minutes=60`);
      // Handle streaming response (NDJSON)
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const lines = decoder.decode(value).split('\n');
        lines.forEach(line => {
          if (line.trim()) {
            const segment = JSON.parse(line);
            setCurrentSegment(segment);
            // In a real app, you'd play audio here
            console.log('Playing:', segment);
          }
        });
      }
    } catch (error) {
      console.error('Stream error:', error);
    }
  };

  const generateHostSegment = async (context) => {
    try {
      // context/topic are query params on the backend (plain function args,
      // no request-body model), not a JSON body.
      const response = await fetch(`${API_BASE}/generate/host-segment?${new URLSearchParams({ context })}`, {
        method: 'POST'
      });
      const segment = await response.json();
      setCurrentSegment(segment);
    } catch (error) {
      console.error('Error generating segment:', error);
    }
  };

  const handleSliderChange = (key, value) => {
    const newConfig = { ...config, [key]: parseFloat(value) };
    // Normalize so total doesn't exceed 1.0
    const total = newConfig.music_weight + newConfig.news_weight + newConfig.ad_weight;
    if (total > 1.0) {
      const scale = 1.0 / total;
      newConfig.music_weight *= scale;
      newConfig.news_weight *= scale;
      newConfig.ad_weight *= scale;
    }
    updateConfig(newConfig);
  };

  const handleContextChange = (context) => {
    updateConfig({ ...config, context });
  };

  const contextModes = [
    { id: 'workout', label: '🏃 Workout', desc: 'Music + motivation' },
    { id: 'commute', label: '🚗 Commute', desc: 'Music + news + banter' },
    { id: 'chill', label: '☕ Chill', desc: 'Laid-back vibes' },
    { id: 'custom', label: '⚙️ Custom', desc: 'Full control' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
      {/* Header */}
      <div className="max-w-4xl mx-auto mb-8">
        <div className="flex items-center gap-3 mb-6">
          <Radio className="w-8 h-8 text-cyan-400" />
          <h1 className="text-4xl font-bold tracking-tight">Your Station</h1>
        </div>
        <p className="text-slate-400">Personalized 24/7 radio, generated just for you</p>
      </div>

      {/* Main Control Panel */}
      <div className="max-w-4xl mx-auto grid gap-6">
        
        {/* Now Playing */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Now Playing</h2>
            <button
              onClick={togglePlayback}
              className="bg-cyan-500 hover:bg-cyan-600 text-white rounded-full p-4 transition"
            >
              {isPlaying ? (
                <Pause className="w-6 h-6" />
              ) : (
                <Play className="w-6 h-6" />
              )}
            </button>
          </div>
          
          {currentSegment ? (
            <div className="bg-slate-700 rounded p-4">
              <p className="text-sm text-cyan-400 mb-2">{currentSegment.type}</p>
              <p className="text-slate-200">
                {/* /generate/host-segment returns text at the top level;
                    /stream/session segments nest it under content
                    (content.text for spoken segments, artist/title for music) */}
                {currentSegment.text
                  || currentSegment.content?.text
                  || (currentSegment.content?.artist && `${currentSegment.content.artist} - ${currentSegment.content.title}`)
                  || ''}
              </p>
              {currentSegment.host && (
                <p className="text-xs text-slate-500 mt-2">Host: {currentSegment.host}</p>
              )}
            </div>
          ) : (
            <div className="bg-slate-700 rounded p-4 text-slate-400">
              Press play to start your station
            </div>
          )}
        </div>

        {/* Context/Mode Selection */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">What are you doing?</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {contextModes.map(mode => (
              <button
                key={mode.id}
                onClick={() => handleContextChange(mode.id)}
                className={`p-4 rounded-lg border-2 transition text-left ${
                  config.context === mode.id
                    ? 'border-cyan-400 bg-slate-700'
                    : 'border-slate-700 bg-slate-900 hover:border-slate-600'
                }`}
              >
                <div className="font-semibold">{mode.label}</div>
                <div className="text-xs text-slate-400">{mode.desc}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Content Mix Sliders */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-6">Content Mix</h3>
          <div className="space-y-6">
            
            {/* Music */}
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-medium">Music</label>
                <span className="text-cyan-400 font-semibold">
                  {Math.round(config.music_weight * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.music_weight}
                onChange={(e) => handleSliderChange('music_weight', e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, rgb(34, 197, 94) 0%, rgb(34, 197, 94) ${config.music_weight * 100}%, rgb(51, 65, 85) ${config.music_weight * 100}%, rgb(51, 65, 85) 100%)`
                }}
              />
              <p className="text-xs text-slate-500 mt-2">How much music vs talk</p>
            </div>

            {/* News */}
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-medium">News & Current Events</label>
                <span className="text-cyan-400 font-semibold">
                  {Math.round(config.news_weight * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.news_weight}
                onChange={(e) => handleSliderChange('news_weight', e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, rgb(59, 130, 246) 0%, rgb(59, 130, 246) ${config.news_weight * 100}%, rgb(51, 65, 85) ${config.news_weight * 100}%, rgb(51, 65, 85) 100%)`
                }}
              />
              <p className="text-xs text-slate-500 mt-2">Headlines and banter</p>
            </div>

            {/* Ads */}
            <div>
              <div className="flex justify-between mb-2">
                <label className="text-sm font-medium">Hilarious Ad Reads</label>
                <span className="text-cyan-400 font-semibold">
                  {Math.round(config.ad_weight * 100)}%
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={config.ad_weight}
                onChange={(e) => handleSliderChange('ad_weight', e.target.value)}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, rgb(236, 72, 153) 0%, rgb(236, 72, 153) ${config.ad_weight * 100}%, rgb(51, 65, 85) ${config.ad_weight * 100}%, rgb(51, 65, 85) 100%)`
                }}
              />
              <p className="text-xs text-slate-500 mt-2">Fake product ads & absurdity</p>
            </div>
          </div>
        </div>

        {/* Host & Personality */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Host Personality</h3>
          <div className="grid grid-cols-2 gap-4 mb-6">
            {['alex', 'jordan'].map(host => (
              <button
                key={host}
                onClick={() => updateConfig({ ...config, host_personality: host })}
                className={`p-4 rounded-lg border-2 transition capitalize ${
                  config.host_personality === host
                    ? 'border-cyan-400 bg-slate-700'
                    : 'border-slate-700 bg-slate-900 hover:border-slate-600'
                }`}
              >
                <div className="font-semibold">{host}</div>
                <div className="text-xs text-slate-400 mt-1">
                  {host === 'alex' ? 'Sassy & witty' : 'Smooth & sardonic'}
                </div>
              </button>
            ))}
          </div>
          
          <div className="space-y-2">
            <button
              onClick={() => generateHostSegment('motivation')}
              className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded border border-slate-600 text-sm transition"
            >
              🎤 Generate Motivation Snippet
            </button>
            <button
              onClick={() => generateHostSegment('ad_lib')}
              className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded border border-slate-600 text-sm transition"
            >
              😄 Generate Fake Ad
            </button>
            <button
              onClick={() => generateHostSegment('transition')}
              className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded border border-slate-600 text-sm transition"
            >
              🎵 Generate Transition
            </button>
          </div>
        </div>

        {/* Scheduling */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
          <button
            onClick={() => setShowSchedule(!showSchedule)}
            className="flex items-center gap-2 text-lg font-semibold mb-4 hover:text-cyan-400 transition"
          >
            <Clock className="w-5 h-5" />
            Schedule (Optional)
          </button>
          
          {showSchedule && (
            <div className="bg-slate-700 rounded p-4 text-sm text-slate-300">
              <p className="mb-3">Set different modes for different times of day</p>
              <div className="space-y-2">
                <div className="flex gap-2">
                  <input type="time" defaultValue="06:00" className="bg-slate-800 rounded px-2 py-1" />
                  <select className="bg-slate-800 rounded px-2 py-1">
                    <option>Workout</option>
                    <option>Commute</option>
                    <option>Chill</option>
                  </select>
                </div>
                <p className="text-xs text-slate-500">More scheduling features coming soon</p>
              </div>
            </div>
          )}
        </div>

        {/* Status */}
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 text-sm text-slate-400">
          <p>🔗 Plex Connected · 📊 Last.fm Synced · 📡 Ready to Stream</p>
        </div>
      </div>
    </div>
  );
};

export default RadioDashboard;
