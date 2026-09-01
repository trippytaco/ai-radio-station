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
# Use the public/reverse-proxied URL, not a LAN IP - the container runs
# on an isolated custom bridge network that can't route to a LAN address.
PLEX_URL=https://plex.orosz.cc
PLEX_TOKEN=your_plex_token_here

# Last.fm Configuration
LASTFM_API_KEY=your_api_key
LASTFM_USERNAME=your_username

# Anthropic (Claude) Configuration
ANTHROPIC_API_KEY=your_api_key

# TTS Configuration (optional - degrades gracefully to text-only if unset)
TTS_PROVIDER=google                        # "google" or "elevenlabs"
GOOGLE_CLOUD_CREDENTIALS_JSON=              # see "Getting Credentials" below
ELEVENLABS_API_KEY=optional

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

### Google Cloud TTS

`GOOGLE_CLOUD_CREDENTIALS_JSON` holds the *content* of your service
account key, not a path to a file on disk - this deploy has no
persistent file storage to point a path at (everything is configured via
Portainer's environment variable UI, same as the other credentials).

1. Download your service account key JSON from the Google Cloud Console
   (IAM & Admin → Service Accounts → Keys)
2. Base64-encode it to a single line, so it pastes cleanly into
   Portainer's env var field without newline/quoting issues:
   ```bash
   base64 -w0 service-account-key.json
   ```
   (macOS: `base64 -i service-account-key.json`)
3. Paste that output as the value of `GOOGLE_CLOUD_CREDENTIALS_JSON` in
   Portainer → Stacks → ai-radio-station → environment variables
4. Set `TTS_PROVIDER=google` (the default)

Pasting the raw JSON directly (starting with `{`) also works, but
base64 is recommended - Portainer's field is single-line and the raw
key contains newlines.

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
│   ├── radio_api.py           # FastAPI server
│   ├── tts_service.py         # Google Cloud / ElevenLabs TTS
│   ├── plex_client.py         # Plex library + streaming
│   ├── news_service.py        # BBC / Guardian / CNN headlines
│   └── radio_queue.py         # Session building, segment queue
├── frontend/                  # Vite + React + Tailwind PWA (RadioMe)
│   ├── src/
│   ├── Dockerfile              # Multi-stage: node build -> nginx serve
│   └── nginx.conf
├── tests/                     # pytest suite (backend) - see "Automated Tests"
├── Dockerfile                  # Backend container config (currently unused
│                                # by docker-compose.yml's ai-radio service,
│                                # which fetches code at container start instead)
├── docker-compose.yml          # Backend + frontend, single stack
├── docker-compose.frontend.yml # Frontend-only fallback for hosts with no
│                                # git binary - see scripts/deploy-frontend.sh
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
└── README.md                   # This file
```

---

## Deployment

### Docker Compose (Recommended)

```bash
docker compose up -d
```

Builds and starts both `ai-radio` (backend) and `ai-radio-frontend`
(the PWA, served on port 8090) from a single `docker-compose.yml`. This
needs a `git` binary on the Docker host itself - the frontend service
builds via a git-context (`build: context: <repo-url>#main:frontend`),
and Docker's BuildKit shells out to the host's own git for that. No git
on the host, no build.

### Portainer (GUI)

Stacks → Add Stack → paste `docker-compose.yml` → add the environment
variables listed at the top of that file → Deploy. Updating either
service later means re-pasting and "Update the stack" - a plain restart
doesn't pick up code or env var changes, only a full stack update does.

### No git on the Docker host?

Use `docker-compose.frontend.yml` + `scripts/deploy-frontend.sh` instead
for the frontend (backend is unaffected either way - it fetches its own
code via `git clone` inside the running container, which only needs git
inside that container's image, not on the host). The script clones
through an `alpine/git` container rather than needing git installed
anywhere on the host itself:

```bash
./scripts/deploy-frontend.sh
```

Re-run it any time to pick up frontend changes; it's idempotent (pulls if
already cloned, clones fresh otherwise).

---

## Next Steps

### Done
- [x] Backend API: Plex, Last.fm, news (BBC/Guardian/CNN), Claude-generated
      host segments
- [x] Text-to-Speech for host voiceovers (Google Cloud / ElevenLabs)
- [x] RadioMe frontend: real Vite/React/Tailwind PWA, background audio
      playback (music queue + generated segment audio), mix sliders,
      context presets, host toggles, topics & news, PWA install
- [x] Single-stack Docker/Portainer deployment
- [x] pytest suite (62 tests) covering every backend endpoint/module

### Coming
- [ ] Real app icons (currently a placeholder SVG only)
- [ ] Real photography for the hero banners (currently CSS gradient placeholders)
- [ ] Audio mixing/ducking server-side (currently client-side volume ducking only)
- [ ] Frontend automated tests
- [ ] Session recording/playback

### Phase 3 (Future)
- [ ] Predictive content mixing
- [ ] Deep dive news articles
- [ ] Guest hosts
- [ ] Multi-user support
- [ ] Public sharing
- [ ] New segment type: a "caller" phoning in to talk about a movie or a
      current-affairs issue (2026-09-01, not scheduled yet)
- [ ] New segment type: a Triple J Hack-style deep-dive "story of the day"
      (2026-09-01, not scheduled yet)

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

This README is the only doc file in the repo - everything else (deploy
steps, testing, credentials, troubleshooting) lives in the sections
above.

---

**Built with**: FastAPI, React, Claude API, Plex, Last.fm, Docker

Enjoy your personalized radio station! 🎙️
