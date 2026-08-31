# AI Radio Station

A personalized 24/7 radio experience that combines your Plex music library, Last.fm listening history, and AI-generated host personalities using Claude (Anthropic).

## Features

🎵 **Music Streaming**
- Stream music directly from your Plex library
- Learns from your Last.fm taste profile

🤖 **AI Hosts**
- Claude-powered host personalities (Alex, Jordan)
- Sassy banter, news commentary, hilarious fake ads
- Speaks directly to you (you're their only listener!)

📰 **Dynamic Content**
- News headlines with host commentary
- Motivational snippets for workouts
- Funny product ads (fictional and real)
- Smooth transitions between segments

🎚️ **Full Control**
- Adjust content mix: Music / News / Ads (%)
- Select host personality
- Choose context: Workout / Commute / Chill
- Optional scheduling for different times

---

## Quick Start

### Prerequisites

- Docker & Docker Compose (or Portainer)
- Plex Media Server with a valid token
- Last.fm account with API key
- Anthropic API key (Claude)

### Setup via Portainer (Easiest)

1. Open Portainer: `http://192.168.8.113:9000`
2. Go to **Stacks** → **Add Stack**
3. Paste `docker-compose.yml` content
4. Add environment variables:
   - `PLEX_TOKEN`
   - `LASTFM_API_KEY`
   - `LASTFM_USERNAME`
   - `ANTHROPIC_API_KEY`
5. Click **Deploy**

### Setup via Docker Compose

```bash
# Clone the repo
git clone https://github.com/trippytaco/ai-radio-station.git
cd ai-radio-station

# Configure credentials
cp .env.example .env
nano .env  # Add your API keys

# Deploy
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

---

## API Endpoints

### Health & Config
- `GET /health` - Health check
- `GET /config` - Get current configuration
- `POST /config` - Update configuration

### Music & Listening
- `GET /plex/library` - Your Plex music library
- `GET /lastfm/recent` - Recent tracks from Last.fm
- `GET /lastfm/top-artists` - Your top artists

### Content Generation
- `POST /generate/host-segment` - Generate AI host segment
  - `context`: "motivation", "news_banter", "ad_lib", "transition"
- `GET /stream` - Get personalized radio stream

---

## Environment Variables

Create a `.env` file with:

```bash
# Plex Configuration
PLEX_URL=http://localhost:32400
PLEX_TOKEN=your_plex_token_here

# Last.fm Configuration
LASTFM_API_KEY=your_api_key
LASTFM_USERNAME=your_username

# Anthropic (Claude) Configuration
ANTHROPIC_API_KEY=your_api_key

# Optional: News Sources
BBC_URL=https://www.bbc.com/news
GUARDIAN_API_KEY=optional
NEWSAPI_KEY=optional

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=false
```

---

## Getting Credentials

### Plex Token
1. Go to https://www.plex.tv/claim
2. Copy the claim code
3. You'll get your token

### Last.fm
1. Create app: https://www.last.fm/api/account/create
2. Copy API Key
3. Get your username from your Last.fm profile

### Anthropic (Claude)
1. Go to https://console.anthropic.com
2. Create API key in account settings
3. Copy the key

---

## Architecture

```
Frontend (React)
    ↓
API Server (FastAPI)
    ├── Plex Integration (Music Library)
    ├── Last.fm Integration (Taste Profile)
    ├── Claude AI (Host Generation)
    └── News Sources (Headlines)
    ↓
Docker Container
    ↓
Your QNAP / Server
```

---

## Host Personalities

### Alex 🎤
- Sassy, witty, irreverent
- Makes pop culture references
- Calls you out playfully
- Best for: Workouts, mornings

### Jordan 🎙️
- Smooth, sardonic, insider vibe
- Laid-back, conversational
- Witty but not exhausting
- Best for: Commutes, focus sessions

---

## Content Modes

### Workout
- 70% music + motivational snippets
- High energy, push to keep going
- Occasional funny ads

### Commute
- 50% music + 35% news + 10% ads
- Mix of songs and host banter
- News headlines with commentary

### Chill
- 80% music + 15% news + 5% ads
- Relaxed, smooth transitions
- Occasional interesting news

### Custom
- Adjust each slider exactly how you want
- Full control over content mix

---

## Testing the API

`context`/`topic` on `/generate/host-segment` are query parameters, not a
JSON body (the endpoint has no request-body model) - pass them on the URL:

```bash
# Health check
curl http://localhost:8000/health

# Get configuration
curl http://localhost:8000/config

# Generate a motivation snippet
curl -X POST "http://localhost:8000/generate/host-segment?context=motivation"

# Generate a fake ad
curl -X POST "http://localhost:8000/generate/host-segment?context=ad_lib"

# Get recent tracks from Last.fm
curl "http://localhost:8000/lastfm/recent?limit=10"
```

---

## Automated Tests

A pytest suite lives in `tests/`. External calls (Anthropic, Plex,
Last.fm, news APIs, TTS providers) are mocked via
[respx](https://lundberg.github.io/respx/), so the suite needs no
credentials and makes zero network calls:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest tests/ -v
```

There's also an opt-in smoke-test module, `tests/test_live_smoke.py`,
that hits a real running instance (e.g. the QNAP deployment) over HTTP
using whatever credentials it actually has configured. It's skipped by
default; run it explicitly against a live instance after a deploy:

```bash
AI_RADIO_LIVE_URL=http://192.168.8.113:8000 \
  .venv/bin/pytest tests/test_live_smoke.py -v -m live
```

When adding a new endpoint or backend module, add coverage in `tests/`
alongside it - the mocked suite is meant to catch exactly the kind of
"looked fine in code review, broke on first real request" bugs this
project has hit before (retired model ids, a frontend/backend query-param
mismatch, an infinite loop when no content sources were configured).

---

## Development

### Local Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python backend/radio_api.py
```

### Project Structure

```
ai-radio-station/
├── backend/
│   └── radio_api.py           # FastAPI server
├── frontend/
│   └── RadioDashboard.jsx     # React dashboard
├── Dockerfile                 # Container config
├── docker-compose.yml         # Docker orchestration
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md                 # This file
```

---

## Deployment

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

### Portainer (GUI)

See `PORTAINER_QUICK_START.md` for step-by-step guide.

### QNAP Deployment

See `SSH_DEPLOYMENT_GUIDE.md` for full setup on QNAP.

---

## Next Steps

### Phase 1 (Current)
- [x] Backend API with Plex + Last.fm + Claude
- [x] Dashboard UI for controls
- [x] Docker configuration
- [x] Portainer deployment guide

### Phase 2 (Coming)
- [ ] Text-to-Speech for host voiceovers (ElevenLabs/Google)
- [ ] Audio mixing (music + voiceover)
- [ ] Real streaming audio output
- [ ] Session recording/playback

### Phase 3 (Future)
- [ ] Predictive content mixing
- [ ] Deep dive news articles
- [ ] Guest hosts
- [ ] Multi-user support
- [ ] Public sharing

---

## Troubleshooting

### Container won't start
1. Check logs: `docker logs ai-radio-station`
2. Verify environment variables
3. Check Docker is running

### API not responding
1. Wait 30 seconds for startup
2. Check health: `curl http://localhost:8000/health`
3. Review logs for errors

### Credentials not working
1. Verify Plex token is valid
2. Check Last.fm API key and username
3. Confirm Anthropic API key is active

---

## License

MIT

---

## Support

For issues, check:
- `README.md` - This file
- `PORTAINER_QUICK_START.md` - Portainer deployment
- `SETUP.md` - Full setup guide
- `ADVANCED.md` - Advanced features

---

**Built with**: FastAPI, React, Claude API, Plex, Last.fm, Docker

Enjoy your personalized radio station! 🎙️
