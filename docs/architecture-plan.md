# Implementation Plan: OracleGG - League of Legends Real-Time Coaching Tool

Last updated: 2026-03-28

---

## Overview

OracleGG is a desktop-local League of Legends coaching tool that operates across three game phases: champion select (via LCU API), in-game (via Live Client Data API), and post-game (via Match-V5). It scouts enemies, recommends comp-specific builds, delivers adaptive in-game tips, and tracks performance trends. The architecture is a Python backend with SQLite storage, served through a local web UI for fastest path to working prototype.

---

## Analysis

### Requirements

- Detect champion select automatically via LCU lockfile polling
- Scout all enemy players (rank, match history, champion mastery, tendencies)
- Recommend builds specific to enemy team composition, not generic "best build"
- Poll Live Client Data API every 3-5 seconds for real-time game state
- Generate contextual tips based on item purchases, gold leads, objectives, game time
- Suggest item pivots when game state shifts (e.g., enemy stacking armor -> suggest armor pen)
- Post-game timeline analysis and personal trend tracking
- Weekly data pipeline to aggregate Master+ builds per champion x enemy comp archetype
- Must work on dev API key (20/sec, 100/2min) during prototyping

### Technical Considerations

- **LCU API requires lockfile parsing**: The League client writes a lockfile with port and auth token. Must poll for its existence and read credentials on startup.
- **Live Client Data API uses a self-signed cert**: Requests to `https://127.0.0.1:2999` will fail SSL verification. Must disable SSL verify or trust the Riot root cert.
- **Rate limiting is the primary bottleneck**: Scouting 5 enemies means: 5 Account-V1 calls + 5 Summoner-V4 calls + 5 League-V4 calls + 5 Champion-Mastery-V4 calls + 25-50 Match-V5 calls (5 match IDs + 5 match details per player). That is 45-70 calls during a ~60-second champ select window. With dev key limits (20/sec, 100/2min), this is tight but feasible if we prioritize and cache aggressively.
- **Meraki Analytics over Data Dragon**: DDragon stats are unreliable. Meraki provides accurate champion and item data. Cache it locally, refresh on patch days.
- **Enemy comp archetypes**: Rather than matching exact 5-champion combos (too sparse), bucket enemy comps into archetypes: heavy AP, heavy AD, poke, engage, split-push, etc. Based on champion tags and historical play patterns.
- **SQLite is the right call for MVP**: All data is local. No multi-user concerns. SQLite handles the read-heavy workload well. Migration to PostgreSQL only needed if we build a shared service later.

### Integration Points

- **Riot Remote APIs**: Account-V1, Summoner-V4, League-V4, Champion-Mastery-V4, Match-V5 (all rate-limited, require API key)
- **LCU API**: Local WebSocket + REST, lockfile auth, random port
- **Live Client Data API**: `https://127.0.0.1:2999`, no auth, self-signed SSL
- **Meraki Analytics CDN**: Static JSON, cache locally
- **Data Dragon CDN**: Images and ID mappings only

---

## Architecture Decisions

### Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.12+ | Fastest prototyping. Best Riot API library ecosystem. ML ecosystem for later phases. |
| **Web framework** | FastAPI | Async-native, WebSocket support built-in, auto-generated API docs, minimal boilerplate. |
| **HTTP client** | httpx | Async HTTP client, connection pooling, timeout control. Better than requests for async FastAPI. |
| **Database** | SQLite via aiosqlite + SQLAlchemy (async) | Local-only, zero config, good read performance. aiosqlite keeps the event loop unblocked. |
| **Frontend** | HTML + HTMX + Tailwind CSS (served by FastAPI) | No build step. HTMX gives real-time partial updates via SSE/WebSocket without React complexity. Visible in any browser tab alongside the game. |
| **Task scheduling** | APScheduler | In-process scheduler for polling loops (LCU, live game) and weekly data pipeline. No external dependency like Celery. |
| **LCU connection** | lcu-driver or manual lockfile + WebSocket | lcu-driver is a Python library that handles lockfile parsing and WebSocket subscriptions. If it is unmaintained, we roll our own (it is ~100 lines). |
| **Rate limiter** | Custom token bucket | Must respect both per-second and per-2-minute Riot limits. httpx middleware or a wrapper. |
| **Package manager** | uv | Fastest Python package manager. Replaces pip, pip-tools, virtualenv. |
| **Migrations** | Alembic | Standard SQLAlchemy migration tool. |

### Alternatives Considered and Rejected

- **Electron/Tauri overlay**: Adds massive complexity for MVP. A browser tab works. Overlay can be Phase 3.
- **Overwolf**: Locked into their ecosystem, revenue sharing, approval process. Not appropriate for rapid prototyping.
- **Django**: Too heavy. We do not need an ORM-first admin-panel framework. FastAPI is leaner and async-native.
- **riotwatcher / cassiopeia**: cassiopeia is powerful but opinionated and heavy. riotwatcher is a thin wrapper but synchronous. We will write our own thin async client with httpx -- it is ~200 lines and gives us full control over caching and rate limiting.
- **PostgreSQL**: Overkill for single-user local app. SQLite is embedded and zero-config.
- **React/Vue frontend**: Requires a build step, node_modules, bundler config. HTMX + server-rendered HTML gets us 90% of the interactivity with 10% of the complexity.

---

## Database Schema

### Core Tables

```sql
-- Static data cache (refreshed on patch)
CREATE TABLE champions (
    id INTEGER PRIMARY KEY,          -- Riot champion ID (e.g., 266 for Aatrox)
    name TEXT NOT NULL,
    key TEXT NOT NULL,                -- Internal key (e.g., "Aatrox")
    tags TEXT NOT NULL,               -- JSON array: ["Fighter", "Tank"]
    stats TEXT NOT NULL,              -- JSON: full Meraki stats blob
    abilities TEXT NOT NULL,          -- JSON: ability data from Meraki
    patch TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE items (
    id INTEGER PRIMARY KEY,          -- Riot item ID
    name TEXT NOT NULL,
    stats TEXT NOT NULL,              -- JSON: item stats from Meraki
    tags TEXT NOT NULL,               -- JSON array: ["Damage", "CriticalStrike"]
    gold_total INTEGER NOT NULL,
    gold_base INTEGER NOT NULL,
    builds_from TEXT,                 -- JSON array of item IDs
    builds_into TEXT,                 -- JSON array of item IDs
    patch TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Aggregated high-elo build data (weekly pipeline)
CREATE TABLE build_aggregates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    champion_id INTEGER NOT NULL,
    role TEXT NOT NULL,               -- "TOP", "JUNGLE", "MID", "ADC", "SUPPORT"
    enemy_comp_archetype TEXT NOT NULL, -- "heavy_ap", "heavy_ad", "balanced", "poke", "engage", "split"
    sample_size INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    -- Build path: ordered list of items
    item_build_path TEXT NOT NULL,    -- JSON array of item IDs in purchase order
    boots_id INTEGER,
    -- Skill order
    skill_order TEXT NOT NULL,        -- JSON array: ["Q","W","E","Q","Q","R",...] first 18 levels
    skill_max_order TEXT NOT NULL,    -- e.g., "Q>E>W"
    -- Starting items
    starting_items TEXT NOT NULL,     -- JSON array of item IDs
    -- Summoner spells
    summoner_spells TEXT NOT NULL,    -- JSON array: [4, 12] (Flash + Teleport)
    -- Runes
    primary_rune_tree TEXT NOT NULL,
    primary_keystone INTEGER NOT NULL,
    primary_runes TEXT NOT NULL,      -- JSON array
    secondary_rune_tree TEXT NOT NULL,
    secondary_runes TEXT NOT NULL,    -- JSON array
    stat_shards TEXT NOT NULL,        -- JSON array
    -- Metadata
    patch TEXT NOT NULL,
    region TEXT NOT NULL DEFAULT 'all',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (champion_id) REFERENCES champions(id)
);

CREATE INDEX idx_build_agg_lookup ON build_aggregates(champion_id, role, enemy_comp_archetype, patch);

-- Player scouting cache (TTL-based)
CREATE TABLE player_cache (
    puuid TEXT PRIMARY KEY,
    game_name TEXT NOT NULL,
    tag_line TEXT NOT NULL,
    summoner_id TEXT,
    rank_solo TEXT,                   -- e.g., "Gold II 45LP"
    rank_flex TEXT,
    profile_icon_id INTEGER,
    summoner_level INTEGER,
    last_fetched TIMESTAMP NOT NULL,
    data TEXT NOT NULL                -- JSON: full scouting report
);

CREATE TABLE match_history_cache (
    match_id TEXT PRIMARY KEY,
    data TEXT NOT NULL,               -- JSON: full match DTO
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scouting reports (generated per champ select)
CREATE TABLE scouting_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT,                     -- LCU game ID if available
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    our_team TEXT NOT NULL,           -- JSON: [{champion_id, summoner_name, role}]
    enemy_team TEXT NOT NULL,         -- JSON: [{champion_id, summoner_name, role, scouting_data}]
    recommendations TEXT NOT NULL,    -- JSON: build, tips, etc.
    phase TEXT NOT NULL DEFAULT 'champ_select' -- "champ_select", "in_game", "post_game"
);

-- Personal performance tracking
CREATE TABLE personal_matches (
    match_id TEXT PRIMARY KEY,
    champion_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    win BOOLEAN NOT NULL,
    kills INTEGER, deaths INTEGER, assists INTEGER,
    cs INTEGER,
    cs_per_min REAL,
    vision_score INTEGER,
    damage_dealt INTEGER,
    damage_taken INTEGER,
    gold_earned INTEGER,
    game_duration INTEGER,            -- seconds
    items_final TEXT NOT NULL,        -- JSON array
    enemy_champion_ids TEXT NOT NULL,  -- JSON array of 5 enemy champ IDs
    timeline_summary TEXT,            -- JSON: key moments, power spikes, mistakes
    played_at TIMESTAMP NOT NULL,
    patch TEXT NOT NULL,
    FOREIGN KEY (champion_id) REFERENCES champions(id)
);

CREATE INDEX idx_personal_champion ON personal_matches(champion_id, played_at DESC);

-- In-game snapshots (for post-game review)
CREATE TABLE game_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT,                    -- linked after game ends
    game_time_secs REAL NOT NULL,
    snapshot_data TEXT NOT NULL,      -- JSON: full game state at this moment
    tips_generated TEXT,              -- JSON: tips produced at this snapshot
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences
CREATE TABLE user_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### Key Design Decisions

1. **JSON columns for flexible nested data**: SQLite handles JSON well with `json_extract()`. Avoids excessive normalization for data that is always read as a unit.
2. **Player cache with TTL**: Scouting data is cached by PUUID. Re-fetch if `last_fetched` is older than 1 hour (configurable). Avoids burning rate limits on repeat lookups.
3. **Build aggregates indexed on the lookup pattern**: The primary query is `(champion_id, role, enemy_comp_archetype, patch)`. Single index covers it.
4. **Game snapshots are append-only**: One row every 3-5 seconds during a game. ~600-1000 rows per 30-min game. Trivial for SQLite.

---

## Project Structure

```
oraclegg/
├── pyproject.toml                  # uv/pip project config
├── alembic.ini                     # DB migration config
├── alembic/
│   └── versions/                   # Migration scripts
├── .env                            # RIOT_API_KEY, config
├── .env.example                    # Template with comments
├── src/
│   └── oraclegg/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app, startup/shutdown, mount routes
│       ├── config.py               # Settings via pydantic-settings, loads .env
│       ├── db/
│       │   ├── __init__.py
│       │   ├── engine.py           # SQLAlchemy async engine + session factory
│       │   ├── models.py           # SQLAlchemy ORM models
│       │   └── queries.py          # Reusable query functions (get_build, cache_player, etc.)
│       ├── riot/
│       │   ├── __init__.py
│       │   ├── client.py           # Async Riot API client (httpx), handles auth + rate limiting
│       │   ├── rate_limiter.py     # Token bucket rate limiter (app-level + method-level)
│       │   ├── lcu.py              # LCU lockfile reader, REST + WebSocket client
│       │   ├── live_client.py      # Live Client Data API poller (localhost:2999)
│       │   ├── endpoints.py        # Riot API endpoint definitions + URL builders
│       │   └── types.py            # Pydantic models for API responses (MatchDTO, SummonerDTO, etc.)
│       ├── static_data/
│       │   ├── __init__.py
│       │   ├── manager.py          # Fetch + cache Data Dragon / Meraki data
│       │   ├── champions.py        # Champion data access (stats, abilities, tags)
│       │   └── items.py            # Item data access (stats, build paths, tags)
│       ├── scouting/
│       │   ├── __init__.py
│       │   ├── scout.py            # Orchestrates enemy scouting (match history, mastery, rank)
│       │   ├── analyzer.py         # Analyzes match history for tendencies (one-trick, tilted, etc.)
│       │   └── comp.py             # Team composition analysis (archetype classification)
│       ├── recommender/
│       │   ├── __init__.py
│       │   ├── builds.py           # Build recommendation engine (queries aggregates, filters by comp)
│       │   ├── tips.py             # In-game tip generation (rules engine)
│       │   ├── item_pivot.py       # Item pivot suggestions based on game state changes
│       │   └── rules/
│       │       ├── __init__.py
│       │       ├── item_triggers.py    # "Enemy bought X -> do Y" rules
│       │       ├── objective_rules.py  # Baron/dragon/tower timing rules
│       │       ├── gold_lead_rules.py  # Ahead/behind strategic tips
│       │       └── power_spike_rules.py # Level/item power spike detection
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── collector.py        # Fetches Master+ matches from Riot API
│       │   ├── aggregator.py       # Processes matches into build_aggregates
│       │   ├── comp_classifier.py  # Classifies enemy team comps into archetypes
│       │   └── scheduler.py        # APScheduler config for weekly runs
│       ├── tracker/
│       │   ├── __init__.py
│       │   ├── personal.py         # Personal performance tracking + trends
│       │   └── post_game.py        # Post-game Match-V5 analysis
│       ├── game_loop/
│       │   ├── __init__.py
│       │   ├── state.py            # In-memory game state machine (IDLE -> CHAMP_SELECT -> IN_GAME -> POST_GAME)
│       │   ├── champ_select.py     # Champ select flow: detect -> scout -> recommend
│       │   ├── in_game.py          # In-game flow: poll -> analyze -> generate tips
│       │   └── post_game.py        # Post-game flow: fetch match -> analyze -> store
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes.py           # FastAPI routes (REST endpoints for frontend)
│       │   ├── websocket.py        # WebSocket endpoint for real-time UI updates
│       │   └── deps.py             # Dependency injection (db session, riot client, etc.)
│       └── ui/
│           ├── templates/
│           │   ├── base.html       # Base layout (Tailwind, HTMX script tags)
│           │   ├── dashboard.html  # Main view: current state, tips, build
│           │   ├── champ_select.html   # Pre-game: scouting report, recommended build
│           │   ├── in_game.html    # In-game: live tips, item tracker, objectives
│           │   ├── post_game.html  # Post-game: match analysis, trends
│           │   ├── settings.html   # User preferences
│           │   └── partials/       # HTMX partial templates (swap targets)
│           │       ├── scouting_card.html
│           │       ├── build_panel.html
│           │       ├── tip_feed.html
│           │       ├── scoreboard.html
│           │       └── trend_chart.html
│           └── static/
│               ├── css/
│               │   └── app.css     # Tailwind build output
│               ├── js/
│               │   └── app.js      # Minimal JS: WebSocket connection, HTMX config
│               └── img/            # Cached champion/item icons from DDragon
├── scripts/
│   ├── run_pipeline.py             # Manual trigger for data pipeline
│   └── seed_static_data.py         # Initial fetch of champion/item data
├── tests/
│   ├── conftest.py
│   ├── test_riot_client.py
│   ├── test_rate_limiter.py
│   ├── test_scouting.py
│   ├── test_recommender.py
│   ├── test_comp_classifier.py
│   └── test_tip_engine.py
└── docs/
    ├── riot-api-research.md        # (existing)
    └── architecture-plan.md        # (this document)
```

---

## Module Responsibilities

### `riot/client.py` - Riot API Client
- Single httpx.AsyncClient instance with connection pooling
- Injects `X-Riot-Token` header on all requests
- Routes requests through `rate_limiter.py` before sending
- Handles 429 responses: reads `Retry-After` header, waits, retries
- Handles 5xx: exponential backoff with 3 retries
- Parses rate limit headers from every response to stay in sync
- Methods: `get_account_by_riot_id()`, `get_summoner_by_puuid()`, `get_match_ids()`, `get_match()`, `get_league_entries()`, `get_champion_mastery()`

### `riot/rate_limiter.py` - Token Bucket Rate Limiter
- Dual bucket: 20 tokens/second + 100 tokens/2 minutes (configurable)
- `async def acquire()`: awaits until a token is available in both buckets
- Refills tokens based on elapsed time
- Thread-safe via asyncio.Lock
- Reads actual limits from response headers (Riot can change limits dynamically)

### `riot/lcu.py` - LCU Client
- Polls for lockfile at known paths: `C:\Riot Games\League of Legends\lockfile` (Windows), equivalent macOS path
- Parses lockfile format: `{processName}:{pid}:{port}:{password}:{protocol}`
- Connects via HTTPS with basic auth (`riot:{password}`) to `https://127.0.0.1:{port}`
- Subscribes to WebSocket events at `wss://127.0.0.1:{port}` for champ select state changes
- Key events: `OnJsonApiEvent_lol-champ-select_v1_session` (fires on every pick/ban change)
- Handles client disconnection gracefully (player closed client)

### `riot/live_client.py` - Live Client Data Poller
- Polls `https://127.0.0.1:2999/liveclientdata/allgamedata` on a configurable interval (default 3 seconds)
- Disables SSL verification (self-signed cert) or pins Riot's root cert
- Detects game start (first successful response) and game end (connection refused after being active)
- Emits structured game state diffs to the game loop
- Tracks: all players' items, levels, scores; game events; game time

### `scouting/scout.py` - Enemy Scouting Orchestrator
- Input: list of 5 enemy summoner identifiers (from LCU champ select data)
- For each enemy (parallelized with asyncio.gather, respecting rate limits):
  1. Resolve Riot ID -> PUUID via Account-V1
  2. Get summoner data via Summoner-V4
  3. Get ranked data via League-V4
  4. Get champion mastery via Champion-Mastery-V4
  5. Get last 10 match IDs via Match-V5
  6. Fetch match details for those 10 matches
- All results cached in `player_cache` and `match_history_cache`
- Passes raw data to `analyzer.py` for tendency extraction

### `scouting/analyzer.py` - Player Tendency Analyzer
- Identifies from match history:
  - **One-trick**: >60% of games on 1-2 champions
  - **First-timing**: 0 recent games on their current pick
  - **Tilted**: 3+ losses in a row, or loss streak with declining KDA
  - **Autofilled**: playing a role they rarely play (based on role distribution)
  - **Win rate on current champion**: self-explanatory
  - **Preferred playstyle**: aggressive (high kills, low vision), passive (high CS, low deaths), roaming (high assists relative to role)

### `scouting/comp.py` - Team Composition Classifier
- Takes 5 champion IDs -> classifies into archetypes
- Archetype taxonomy:
  - `heavy_ap`: 3+ AP damage sources
  - `heavy_ad`: 3+ AD damage sources
  - `balanced`: mixed damage
  - `poke`: 2+ poke champions (Xerath, Jayce, Zoe, Varus, etc.)
  - `engage`: 2+ hard engage (Malphite, Leona, Amumu, etc.)
  - `split_push`: 1+ strong split-pushers with TP (Fiora, Jax, Tryndamere)
  - `protect_carry`: Lulu/Janna/Karma + hypercarry ADC
  - `early_game`: 3+ early-game champions (based on win rate curve data)
  - `scaling`: 3+ late-game scaling champions
- A team can match multiple archetypes (returns ranked list)
- Uses champion tags from Meraki data + a curated override table for edge cases

### `recommender/builds.py` - Build Recommendation Engine
- Input: your champion, your role, enemy comp archetypes
- Queries `build_aggregates` for the best matching entry
- Fallback chain: exact comp archetype match -> `balanced` archetype -> highest overall win rate
- Returns: full item build path (ordered), boots, skill order, runes, summoner spells, starting items
- Includes context: "This build is strong against heavy AP comps because of the early MR from {item}"

### `recommender/tips.py` - In-Game Tip Engine (Rules-Based)
- Consumes game state diffs from `live_client.py`
- Evaluates rules from `rules/` modules against current state
- Deduplicates: same tip not repeated within 60 seconds
- Prioritizes: urgent tips (baron call, enemy power spike) over general tips
- Rate-limits output: max 1 tip every 15 seconds to avoid overwhelming the player

### `recommender/rules/` - Rule Modules
- **item_triggers.py**: Maps enemy item purchases to actionable tips. Example: enemy ADC completes Infinity Edge -> "Enemy {champion} has IE + 60% crit. Avoid extended trades, burst or disengage."
- **objective_rules.py**: Dragon/Baron/Rift Herald timing. "Dragon spawns in 30s, group bot." "Baron is free -- enemy jungler is dead for 25s."
- **gold_lead_rules.py**: Team gold differential -> strategic posture. "Team is 3k gold behind at 15 min. Play safe, scale, avoid 5v5."
- **power_spike_rules.py**: Level-based (6, 11, 16) and item-based power spikes. "You just hit level 6 before enemy laner. Look for an all-in."

### `pipeline/` - Weekly Data Pipeline
- **collector.py**: Fetches Master+ player list via League-Exp-V4. For each player, fetches recent ranked match IDs. Fetches match details. Stores raw data in `match_history_cache`.
- **aggregator.py**: Processes cached matches. For each champion x role x enemy comp archetype: aggregates item build paths, skill orders, runes. Weights by win rate. Stores results in `build_aggregates`.
- **comp_classifier.py**: Reuses `scouting/comp.py` logic to classify enemy teams in historical matches.
- **scheduler.py**: APScheduler job runs every Sunday at 3 AM (configurable). Also provides manual trigger via `scripts/run_pipeline.py`.

### `game_loop/state.py` - Game State Machine
```
IDLE -> CHAMP_SELECT -> IN_GAME -> POST_GAME -> IDLE
         |                                |
         +--- (dodge) -----> IDLE         |
                                          |
         IDLE <---------------------------+
```
- Transitions driven by:
  - IDLE -> CHAMP_SELECT: LCU lockfile detected + champ select session active
  - CHAMP_SELECT -> IN_GAME: Live Client Data API becomes reachable
  - CHAMP_SELECT -> IDLE: champ select session ends without game (dodge/cancel)
  - IN_GAME -> POST_GAME: Live Client Data API becomes unreachable after being active
  - POST_GAME -> IDLE: post-game analysis complete
- Each state has an associated handler module in `game_loop/`

---

## Data Pipeline Design (Weekly Aggregation)

### Overview

The pipeline collects high-elo (Master+) match data and aggregates it into build recommendations per champion, per role, per enemy composition archetype. This is the data that powers the build recommender.

### Pipeline Steps

```
Step 1: Collect Master+ Player List
  - GET /lol/league-exp/v4/entries/RANKED_SOLO_5x5/MASTER/I (paginated)
  - GET /lol/league-exp/v4/entries/RANKED_SOLO_5x5/GRANDMASTER/I
  - GET /lol/league-exp/v4/entries/RANKED_SOLO_5x5/CHALLENGER/I
  - Store summoner IDs. Typical count: ~5,000-15,000 players per region.
  - For MVP: NA region only. Expand later.

Step 2: Fetch Recent Match IDs
  - For each player PUUID:
    GET /lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&count=20
  - Deduplicate match IDs across players (many Master+ players play each other).
  - Target: ~50,000-100,000 unique matches per weekly run.
  - Rate limit strategy: this is the bottleneck. At 100 req/2min (dev key), fetching
    15,000 match ID lists = ~300 minutes = 5 hours. With a personal/production key
    this drops dramatically.

Step 3: Fetch Match Details
  - For each unique match ID:
    GET /lol/match/v5/matches/{matchId}
  - Cache in match_history_cache to avoid re-fetching.
  - Parse: for each of 10 participants, extract champion, role, items (final + purchase order
    from timeline), skill order, runes, summoner spells, win/loss.

Step 4: Classify Enemy Comps
  - For each participant's match: take the 5 enemy champions and classify into archetypes
    using comp_classifier.
  - This runs locally, no API calls.

Step 5: Aggregate
  - Group by: (champion_id, role, enemy_comp_archetype)
  - For each group:
    - Item build path: most common ordered sequence of completed items (excluding components),
      weighted by win rate. Use longest common subsequence or frequency counting.
    - Boots: most common boots choice, weighted by win rate.
    - Skill order: most common first 18 skill points, weighted by win rate.
    - Runes: most common full rune page, weighted by win rate.
    - Starting items: most common starting item set.
    - Summoner spells: most common pair.
    - Overall win rate for this archetype matchup.
    - Sample size (for confidence filtering).
  - Minimum sample size: 30 matches. Below that, fall back to general (non-archetype-specific) data.

Step 6: Store
  - Upsert into build_aggregates table.
  - Tag with current patch version.
  - Keep previous patch data for comparison.
```

### Rate Limit Strategy for Pipeline

With a dev key (100 req/2 min), a full pipeline run is impractical (~50+ hours for 100k matches). Strategies:

1. **MVP approach**: Collect a smaller sample. 500 players x 10 matches = 5,000 matches. Takes ~2 hours. Enough for popular champions but sparse for niche picks.
2. **Personal key approach**: Apply for a personal API key (no review required, higher limits). Cuts pipeline time to hours instead of days.
3. **Incremental collection**: Run collector daily in small batches instead of one weekly burst. 50 players/day across the week = 350 players x 20 matches = 7,000 matches.
4. **Community data sources**: Supplement with data from community APIs (if available and TOS-compliant) for the initial dataset.

Recommendation: Start with MVP approach (small sample + dev key). Apply for personal key immediately. Once approved, switch to full pipeline.

---

## Phase Breakdown

### Phase 0: Skeleton + LCU Detection (Days 1-2)

**Goal**: Project boots up, detects League client, reads champ select state.

**Step 1: Project scaffolding**
- Files: `pyproject.toml`, `.env.example`, `src/oraclegg/__init__.py`, `src/oraclegg/main.py`, `src/oraclegg/config.py`
- Actions:
  - Initialize uv project with dependencies: `fastapi`, `uvicorn`, `httpx`, `aiosqlite`, `sqlalchemy[asyncio]`, `pydantic-settings`, `apscheduler`, `websockets`, `jinja2`
  - Set up config.py with pydantic-settings: `RIOT_API_KEY`, `LCU_PATH`, `DB_PATH`, `POLL_INTERVAL`, `REGION`, `PLATFORM`
  - FastAPI app in main.py with lifespan handler (startup: init DB, start background tasks; shutdown: cleanup)
- Tests: App starts, config loads from .env
- Success: `uv run uvicorn oraclegg.main:app` serves a hello-world page

**Step 2: Database setup**
- Files: `src/oraclegg/db/engine.py`, `src/oraclegg/db/models.py`, `alembic.ini`, `alembic/`
- Actions:
  - Define SQLAlchemy async models matching the schema above
  - Configure Alembic for async SQLite
  - Create initial migration
- Tests: Migration runs, tables exist, basic CRUD works
- Success: `alembic upgrade head` creates all tables

**Step 3: LCU connection**
- Files: `src/oraclegg/riot/lcu.py`, `src/oraclegg/game_loop/state.py`
- Actions:
  - Implement lockfile finder (platform-aware paths)
  - Implement lockfile parser
  - REST client with basic auth + SSL disabled (self-signed cert)
  - WebSocket subscription to champ select events
  - State machine: IDLE <-> CHAMP_SELECT transitions
- Tests: Mock lockfile parsing, mock WebSocket events, state transitions
- Blockers: Need League client running for integration testing
- Success: Console logs "Champ select detected" when entering a lobby

### Phase 1: Scouting + Build Recommendations (Days 3-6) -- **This is the MVP**

**Step 4: Riot API client + rate limiter**
- Files: `src/oraclegg/riot/client.py`, `src/oraclegg/riot/rate_limiter.py`, `src/oraclegg/riot/endpoints.py`, `src/oraclegg/riot/types.py`
- Actions:
  - httpx-based async client with X-Riot-Token auth
  - Dual token bucket rate limiter (20/sec + 100/2min)
  - Pydantic response models for key DTOs (Account, Summoner, Match, League, Mastery)
  - Retry logic for 429/5xx
- Tests: Rate limiter respects both buckets, client retries on 429
- Success: Can fetch a summoner by Riot ID and get their match history

**Step 5: Static data manager**
- Files: `src/oraclegg/static_data/manager.py`, `src/oraclegg/static_data/champions.py`, `src/oraclegg/static_data/items.py`, `scripts/seed_static_data.py`
- Actions:
  - Fetch and cache Data Dragon version list, champion.json, item.json (for ID mappings + images)
  - Fetch and cache Meraki champion and item data (for accurate stats)
  - Store in `champions` and `items` tables
  - Download champion/item icon images to `src/oraclegg/ui/static/img/`
  - Provide lookup functions: `get_champion(id)`, `get_item(id)`, `get_champion_tags(id)`
- Tests: Can resolve champion ID to name, item ID to stats
- Success: `uv run python scripts/seed_static_data.py` populates static data

**Step 6: Enemy scouting**
- Files: `src/oraclegg/scouting/scout.py`, `src/oraclegg/scouting/analyzer.py`, `src/oraclegg/scouting/comp.py`, `src/oraclegg/db/queries.py`
- Actions:
  - Scout orchestrator: resolves all 5 enemies in parallel (respecting rate limits)
  - Player cache with 1-hour TTL
  - Match history cache (permanent, matches are immutable)
  - Tendency analyzer: one-trick, first-timer, tilted, autofilled detection
  - Comp classifier: tag-based archetype detection
- Tests: Mock API responses, verify tendency detection logic, verify comp classification
- Blockers: Rate limits may make real integration tests slow
- Success: Given 5 summoner names, produces a scouting report with rank, win rates, tendencies

**Step 7: Build recommendation engine + initial data**
- Files: `src/oraclegg/recommender/builds.py`, `src/oraclegg/pipeline/collector.py`, `src/oraclegg/pipeline/aggregator.py`, `src/oraclegg/pipeline/comp_classifier.py`, `scripts/run_pipeline.py`
- Actions:
  - Implement pipeline (collector + aggregator) -- start with small sample (500 players)
  - Build recommender: query aggregates by champion + role + enemy archetype
  - Fallback chain when archetype-specific data is sparse
  - Format recommendation: item build path with order + boots + skill order + runes
- Tests: Aggregator produces correct counts from mock match data, recommender returns valid builds
- Success: "Give me the best Jinx ADC build against a heavy AP comp" returns a specific, data-backed answer

**Step 8: Champ select UI**
- Files: `src/oraclegg/ui/templates/`, `src/oraclegg/api/routes.py`, `src/oraclegg/api/websocket.py`, `src/oraclegg/game_loop/champ_select.py`
- Actions:
  - Base HTML template with Tailwind CDN + HTMX script
  - Dashboard page showing current state (idle / champ select / in-game / post-game)
  - Champ select view: enemy scouting cards + recommended build panel
  - WebSocket connection for real-time updates as champ select progresses
  - Wire up game loop: LCU detects champ select -> scout enemies -> push results to UI
- Tests: Manual -- enter a game lobby, see scouting data appear
- **This is the MVP milestone.** At this point, the tool detects champ select, scouts enemies, and recommends a build.

### Phase 2: In-Game Coaching (Days 7-10)

**Step 9: Live Client Data poller**
- Files: `src/oraclegg/riot/live_client.py`, `src/oraclegg/game_loop/in_game.py`
- Actions:
  - Poll `https://127.0.0.1:2999/liveclientdata/allgamedata` every 3 seconds
  - Detect game start (first successful poll) and game end (connection drops after active)
  - Parse response into structured game state
  - Compute diffs between polls (new items purchased, level ups, kills, objective takes)
  - Store snapshots in `game_snapshots` table (every 15 seconds, not every poll)
  - Transition state machine: CHAMP_SELECT -> IN_GAME
- Tests: Mock Live Client responses, verify diff computation
- Success: During a game, console logs item purchases and events as they happen

**Step 10: Tip engine + rules**
- Files: `src/oraclegg/recommender/tips.py`, `src/oraclegg/recommender/item_pivot.py`, `src/oraclegg/recommender/rules/*.py`
- Actions:
  - Rules engine framework: each rule is a function `(game_state, diff, context) -> Optional[Tip]`
  - Item trigger rules (10-15 rules for key item completions)
  - Objective timing rules (dragon, baron, herald spawn timers + death timer awareness)
  - Gold lead rules (play aggressive when ahead, play safe when behind)
  - Power spike rules (level 6/11/16, key item completions for your champion)
  - Item pivot logic: compare your current build path against what you should build given current enemy items
  - Tip deduplication and rate limiting (max 1 per 15s)
  - Tip prioritization (P0: urgent objective calls, P1: enemy power spikes, P2: general strategy)
- Tests: Feed mock game states, verify correct tips fire at correct times
- Success: During a game, contextual tips appear: "Enemy Vayne just completed BOTRK. She wins extended trades now."

**Step 11: In-game UI**
- Files: `src/oraclegg/ui/templates/in_game.html`, `src/oraclegg/ui/templates/partials/tip_feed.html`, `src/oraclegg/ui/templates/partials/scoreboard.html`
- Actions:
  - In-game view: live scoreboard (all 10 players' items + scores), tip feed, objective timers
  - Tips appear as a scrolling feed with priority coloring (red = urgent, yellow = important, blue = info)
  - Current build recommendation shown alongside actual items purchased
  - Item pivot suggestions highlighted when your build should diverge from plan
  - HTMX SSE or WebSocket for real-time updates without full page reloads
- Tests: Manual -- play a game, watch tips flow
- Success: In-game UI updates every 3 seconds with live data and produces useful tips

### Phase 3: Post-Game + Trends (Days 11-13)

**Step 12: Post-game analysis**
- Files: `src/oraclegg/tracker/post_game.py`, `src/oraclegg/game_loop/post_game.py`
- Actions:
  - On game end: wait 30 seconds, then fetch Match-V5 match data + timeline
  - Parse timeline for key moments: first blood, tower kills, dragon/baron takes, teamfights
  - Compare player's actual build to recommended build (did they follow it? when did they deviate?)
  - Calculate performance metrics: CS/min, vision score, KDA, damage share, gold efficiency
  - Store in `personal_matches` table
  - Generate summary: "You were 3/0/2 at 10 min but died 4 times between 15-20 min. Consider playing safer after your power spike."
- Tests: Mock match timeline, verify event extraction and summary generation
- Success: After a game, post-game screen shows match analysis

**Step 13: Performance trends**
- Files: `src/oraclegg/tracker/personal.py`, `src/oraclegg/ui/templates/post_game.html`, `src/oraclegg/ui/templates/partials/trend_chart.html`
- Actions:
  - Query personal_matches for trend data: win rate over last N games, CS/min trend, vision score trend
  - Champion-specific trends: "Your Jinx win rate: 62% over 21 games"
  - Role-specific trends
  - Weakness identification: "Your CS/min drops after 20 minutes consistently"
  - Simple charts using Chart.js (loaded from CDN, no build step needed)
- Tests: Mock match history, verify trend calculations
- Success: Trends page shows meaningful performance data over time

### Phase 4: Polish + Pipeline Automation (Days 14-16)

**Step 14: Pipeline automation + data quality**
- Files: `src/oraclegg/pipeline/scheduler.py`
- Actions:
  - APScheduler cron job for weekly pipeline run
  - Progress logging (X/Y matches processed)
  - Graceful handling of rate limit exhaustion (pause and resume)
  - Data quality checks: minimum sample size filtering, outlier removal
  - Patch version detection: auto-invalidate old build data when new patch detected
- Tests: Pipeline runs end-to-end with small dataset
- Success: Pipeline runs automatically, produces fresh build data

**Step 15: Settings + polish**
- Files: `src/oraclegg/ui/templates/settings.html`, various
- Actions:
  - Settings page: configure Riot API key, preferred region, polling interval, tip frequency
  - Persist settings in `user_settings` table
  - UI polish: loading states, error states, empty states
  - Graceful handling when League client is not running
  - Startup flow: validate API key, check static data freshness, run seed if needed
- Tests: Manual walkthrough of all states
- Success: Tool is usable end-to-end without touching config files

---

## Key Data Flows

### Champ Select Flow (detailed)

```
1. LCU lockfile detected on disk
2. Connect to LCU REST API, verify connection
3. Subscribe to LCU WebSocket: /lol-champ-select/v1/session
4. On champ select session event:
   a. Parse picks/bans for both teams
   b. Extract enemy summoner identifiers
   c. For each enemy (asyncio.gather with semaphore for rate limiting):
      i.   Check player_cache (skip API calls if fresh)
      ii.  Account-V1: riot ID -> PUUID
      iii. Summoner-V4: PUUID -> summoner data
      iv.  League-V4: summoner ID -> rank
      v.   Champion-Mastery-V4: PUUID -> mastery list
      vi.  Match-V5: PUUID -> last 10 match IDs -> match details (check cache first)
   d. Run analyzer on each enemy's data -> tendencies
   e. Classify enemy team comp -> archetypes
   f. Query build_aggregates for your champion + role + enemy archetypes
   g. Push scouting report + build recommendation to UI via WebSocket
5. As picks change (new WebSocket events), re-run steps d-g with updated comp
6. Final recommendation locked when champ select ends (all picks confirmed)
```

### In-Game Flow (detailed)

```
1. Live Client Data API becomes reachable (game loaded)
2. Fetch initial game state: all players, champions, teams
3. Every 3 seconds:
   a. GET /liveclientdata/allgamedata
   b. Parse into structured state
   c. Compute diff from previous state:
      - New items purchased (by any player)
      - Level changes
      - Kill/death/assist events
      - Objective events (dragon, baron, tower, inhibitor)
      - Game time milestones
   d. Run diff through rules engine:
      - item_triggers: check each new enemy item against trigger rules
      - objective_rules: check spawn timers, death timers for objective windows
      - gold_lead_rules: check team gold differential
      - power_spike_rules: check level/item milestones
   e. Collect all generated tips, deduplicate, prioritize
   f. If top tip is different from last shown tip and >15s since last tip:
      Push tip to UI via WebSocket
   g. Check if build pivot is needed:
      - Compare planned build path against enemy items
      - If enemy team is stacking armor and you are AD: suggest armor pen earlier
      - If enemy has healing and you have not built anti-heal: suggest Grievous Wounds
   h. Every 15 seconds: store game snapshot in DB
4. On connection drop (game ended): transition to POST_GAME
```

---

## Configuration (.env)

```bash
# Riot API Configuration
# Get your key at https://developer.riotgames.com/
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Region for remote API calls (americas, europe, asia, sea)
RIOT_REGION=americas

# Platform for platform-routed API calls (na1, euw1, kr, etc.)
RIOT_PLATFORM=na1

# League client install path (auto-detected on Windows if not set)
# LCU_PATH=C:\Riot Games\League of Legends

# Database
DB_PATH=./data/oraclegg.db

# Polling intervals (seconds)
LIVE_CLIENT_POLL_INTERVAL=3
LCU_POLL_INTERVAL=2

# Tip engine
TIP_COOLDOWN_SECONDS=15
MAX_TIPS_PER_MINUTE=4

# Data pipeline
PIPELINE_REGION=na1
PIPELINE_PLAYER_SAMPLE_SIZE=500
PIPELINE_MATCHES_PER_PLAYER=10
PIPELINE_MIN_SAMPLE_SIZE=30

# Server
HOST=127.0.0.1
PORT=8000
```

---

## Testing Strategy

### Unit Tests (pytest + pytest-asyncio)
- Rate limiter: bucket depletion, refill timing, dual bucket enforcement
- Comp classifier: known team comps -> expected archetypes
- Tendency analyzer: mock match histories -> expected labels (one-trick, tilted, etc.)
- Tip rules: mock game states -> expected tips
- Build recommender: mock aggregates -> expected recommendations
- Item pivot logic: mock enemy builds -> expected suggestions

### Integration Tests
- Riot API client against real API (use pytest markers to skip when no key)
- LCU client against mock lockfile
- Full scouting pipeline with cached API responses
- Database CRUD operations

### Manual Testing Checklist
- [ ] Start tool with League client closed -> shows "Waiting for League client"
- [ ] Open League client -> tool detects it
- [ ] Enter champ select -> scouting begins, results appear
- [ ] Complete champ select -> build recommendation finalized
- [ ] Game starts -> live data flows, tips appear
- [ ] Game ends -> post-game analysis appears
- [ ] Check trends page after 5+ games
- [ ] Test with API key expired -> clear error message
- [ ] Test rate limiting under load -> no 429 errors leak through

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Dev API key expires every 24 hours | Config makes key easy to update. Display clear "key expired" error. Apply for personal key ASAP. |
| Live Client Data API changes/breaks | Abstract behind `live_client.py`. Version-check responses. Graceful degradation: in-game tips stop but pre-game still works. |
| LCU API changes port/auth format | Lockfile format has been stable for years. Abstract behind `lcu.py`. |
| Rate limits too tight for scouting 5 enemies | Cache aggressively. Prioritize: scout highest-threat enemy first (by champion, not alphabetically). Stagger requests. |
| Sparse build data for niche champions | Fallback chain: archetype-specific -> general -> most popular build. Show confidence level to user. |
| Meraki Analytics goes offline | Cache locally, serve from cache indefinitely. Fall back to Data Dragon (less accurate but functional). |
| Player data stale in cache | 1-hour TTL on player cache. Match history cache is permanent (matches are immutable). |
| Pipeline takes too long on dev key | Start with 500-player sample. Apply for personal key. Incremental daily collection. |

---

## What This Plan Does NOT Cover (Future Phases)

- **Desktop overlay** (Electron/Tauri): Phase 3+ feature. Browser tab works for now.
- **ML-based tip engine**: Phase 3+. Rules engine is sufficient for MVP and v1.
- **Multi-region support**: MVP is NA-only. Expanding to EUW/KR is a config change + separate pipeline runs.
- **Multi-user / hosted service**: Everything is local-first. Hosted version would need PostgreSQL, user auth, and a production API key.
- **Voice coaching / TTS**: Could read tips aloud. Nice-to-have, not critical.
- **Mobile companion**: Out of scope entirely for now.
- **Rune page auto-import**: LCU API can set rune pages. Nice automation but risky (modifies client state). Defer.

---

## Open Questions to Resolve Before Building

1. **Windows-only or cross-platform?** League runs on Windows and macOS. LCU lockfile paths differ. Live Client Data API works on both. If you only play on Windows, we can skip macOS support and simplify the lockfile detection. What is your setup?

2. **How should tips be surfaced during gameplay?** A browser tab requires alt-tabbing or a second monitor. Options:
   - Second monitor (simplest, if you have one)
   - Windowed/borderless mode + always-on-top browser window (possible with a small ahk/powershell script)
   - Audio cues / TTS for high-priority tips (no visual switching needed)
   - Defer overlay to Phase 3

3. **Initial pipeline run**: Do you want to run the data pipeline first (takes ~2 hours with dev key, produces build data) or hard-code some test build data to get the UI working faster?

4. **Scope of "enemy team comp specific" builds**: The current plan classifies enemy comps into ~9 archetypes. An alternative is per-matchup data (your champion vs each specific enemy champion in lane), which is denser but simpler to aggregate. Do you want both, or start with one?

5. **Do you want a system tray application?** Instead of running `uv run uvicorn ...` from terminal, we could wrap the whole thing in a system tray app (using `pystray`) that auto-starts with the OS. This is polish, but it is low effort and makes the tool feel like a real product.
