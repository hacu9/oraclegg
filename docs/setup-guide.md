# OracleGG Setup and Usage Guide

OracleGG is a real-time League of Legends coaching tool. It collects high-elo match data, generates build recommendations, and provides live in-game overlays with tips, item suggestions, and matchup information.

---

## 1. Prerequisites

- **Python 3.11+**
- **uv** -- install from https://docs.astral.sh/uv/getting-started/installation/
- **Riot API Key** -- get a development key at https://developer.riotgames.com/
  - Sign in with your Riot account, then copy the key from the dashboard.
  - Development keys expire every 24 hours. You will need to regenerate them daily until you apply for a production key.

---

## 2. Installation

```bash
git clone <repo-url> oraclegg
cd oraclegg

# Install all dependencies
uv sync

# Create your config file
cp .env.example .env
```

Open `.env` and set at minimum:

```bash
# Your Riot API key (required)
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Your Riot ID for personal tracking
SUMMONER_RIOT_ID=YourName#TAG

# Region routing: americas, europe, asia, sea
RIOT_REGION=americas

# Platform: na1, la1, la2, euw1, kr, etc.
RIOT_PLATFORM=na1
```

See `.env.example` for all available settings with explanations.

---

## 3. First Run Setup

Run these steps in order.

### 3.1 Seed static data

Downloads champion and item data from Data Dragon and Meraki Analytics into the local SQLite database.

```bash
uv run python scripts/seed_static_data.py
```

This only needs to run once per patch. Re-run after a new League patch drops to pick up new champions, items, or stat changes.

### 3.2 Run the data pipeline

Collects ranked match data from high-elo players and aggregates it into build recommendations.

```bash
uv run python scripts/run_pipeline.py --players 50 --min-sample 5
```

Arguments:

| Flag            | Default | Description                                          |
|-----------------|---------|------------------------------------------------------|
| `--players`     | 50      | Number of Master+ players to sample                  |
| `--platform`    | na1     | Platform to collect from                             |
| `--min-sample`  | 10      | Minimum matches needed for a build to be recommended |

Use `--min-sample 5` for the first run so you get some data even with a small sample. Increase it once you have collected more matches.

### 3.3 Start the server

```bash
uv run uvicorn oraclegg.main:app --host 0.0.0.0 --port 8000
```

The server starts a background game monitor that polls the Live Client Data API every few seconds, so it will automatically detect when a game starts.

---

## 4. WSL2 Setup (Windows Subsystem for Linux)

If you are running OracleGG inside WSL2 while League of Legends runs on the Windows host, you need extra setup. The Live Client Data API binds to `127.0.0.1:2999` on Windows, which is not reachable from WSL2 directly.

### 4.1 Enable the Replay API

Edit League's config file at:

```
C:\Riot Games\League of Legends\Config\game.cfg
```

Add under the `[General]` section:

```ini
[General]
EnableReplayApi=1
```

### 4.2 Allow the port through Windows Firewall

Open PowerShell as Administrator and run:

```powershell
netsh advfirewall firewall add rule name="LoL Live Client WSL" dir=in action=allow protocol=TCP localport=2999
```

### 4.3 Run the WSL bridge on Windows

The bridge is a small HTTP proxy that listens on port 29990 (reachable from WSL) and forwards requests to the Live Client API on port 2999.

Copy `scripts/wsl_bridge.py` to your Windows filesystem (or use the copy at `C:\Users\<you>\wsl_bridge.py`), then run it from a Windows terminal (PowerShell or CMD):

```powershell
python C:\Users\<you>\wsl_bridge.py
```

You should see:

```
WSL Bridge on :29990 -> https://127.0.0.1:2999
```

Leave this running while you play. OracleGG auto-detects WSL2 and tries the bridge on port 29990 before falling back to direct connections. The detection logic reads `/etc/resolv.conf` to find the Windows host IP and tries multiple base URLs in order:

1. `http://<windows-host>:29990` (WSL bridge, preferred)
2. `http://172.25.80.1:29990` (hardcoded fallback)
3. `https://<windows-host>:2999` (direct, may not work from WSL)
4. `https://127.0.0.1:2999` (native only)

### 4.4 Verify the bridge

With a game running, test from inside WSL:

```bash
curl http://$(grep nameserver /etc/resolv.conf | awk '{print $2}'):29990/liveclientdata/allgamedata
```

If you get JSON back, the bridge is working.

---

## 5. Usage

### Dashboard

```
http://127.0.0.1:8000
```

The main landing page. Scout players, look up quick builds, and check aggregated data from the pipeline.

### Champ Select

```
http://127.0.0.1:8000/champ-select
```

Manual matchup builder. Enter your champion and lane opponent to get build recommendations, win rates, and tips. Useful when you want to plan ahead without waiting for champ select detection.

### In-Game Overlay

```
http://127.0.0.1:8000/in-game
```

Live scoreboard with real-time tips and item suggestions. Auto-redirects when a game is detected by the background monitor. The tip engine throttles output to avoid noise (default: 15-second cooldown, max 4 tips per minute -- configurable in `.env`).

### API Docs

```
http://127.0.0.1:8000/docs
```

Auto-generated FastAPI/Swagger documentation for all API endpoints. Useful for debugging or building integrations.

---

## 6. Data Pipeline

### What it does

The pipeline runs in two phases:

1. **Collection** -- Fetches Master+ player lists from the Riot API, then downloads their recent ranked matches. Stores raw match data in the local SQLite database.
2. **Aggregation** -- Processes collected matches to compute per-champion build recommendations: item builds, runes, skill orders, and win rates. Only creates a recommendation if the number of matching games meets the `--min-sample` threshold.

### Running bigger batches

For a fuller dataset:

```bash
uv run python scripts/run_pipeline.py --players 500 --min-sample 30
```

This fetches up to `PIPELINE_MATCHES_PER_PLAYER` (default: 10) matches per player, so 500 players yields up to 5000 matches.

### Rate limits

The Riot development API key has strict rate limits:

- 20 requests per second
- 100 requests per 2 minutes

A production key has significantly higher limits. With a dev key, expect the pipeline to take a while for large batches. The collector handles rate limiting, but if you hit 429 errors, the pipeline will slow down or stop. Consider:

- Running with `--players 50` during development.
- Applying for a production key at https://developer.riotgames.com/ once the tool is working.

### Keeping data fresh

Re-run the pipeline periodically (daily or weekly) to keep build recommendations up to date with the current meta. Re-run `seed_static_data.py` after each new League patch.

---

## 7. Troubleshooting

### Game not detected

- **WSL2**: Make sure `wsl_bridge.py` is running on the Windows side. Check the firewall rule is active.
- **Native Windows/macOS**: The Live Client API only runs during an active game. It starts when loading screen begins and stops when the game ends.
- Check that `EnableReplayApi=1` is in `Config/game.cfg`.
- Try `curl https://127.0.0.1:2999/liveclientdata/allgamedata -k` from the machine running League. If this fails, the client API is not active.

### API key expired

Development keys expire every 24 hours. Go to https://developer.riotgames.com/, regenerate the key, and update `RIOT_API_KEY` in your `.env` file. Restart the server.

### Pipeline returns zero build recommendations

- Lower `--min-sample` (e.g., `--min-sample 3`) to see if data was collected but filtered out.
- Check that `--platform` matches a region with an active Master+ population. NA1 is the default and usually has the largest pool.
- Confirm the API key is valid by running a small batch: `--players 5`.

### Database issues

The SQLite database lives at `./data/oraclegg.db` by default (configurable via `DB_PATH` in `.env`). To start fresh, delete the file and re-run the seed and pipeline scripts.

### LCU (League Client) not connecting

The LCU client reads the lockfile to authenticate. It looks in standard install paths:

- Windows: `C:\Riot Games\League of Legends\lockfile`
- macOS: `/Applications/League of Legends.app/Contents/LoL/lockfile`

If your install is elsewhere, set `LCU_PATH` in `.env` to the League of Legends directory.

### Port conflicts

The server defaults to port 8000. If something else is using it, either stop that process or change `PORT` in `.env`.

---

## Configuration Reference

All settings are in `.env`. Defaults are shown in parentheses.

| Variable                      | Default            | Description                                    |
|-------------------------------|--------------------|------------------------------------------------|
| `RIOT_API_KEY`                | (none)             | Riot API key (required)                        |
| `RIOT_REGION`                 | `americas`         | Regional routing: americas, europe, asia, sea  |
| `RIOT_PLATFORM`               | `la1`              | Platform: na1, la1, la2, euw1, kr, etc.        |
| `SUMMONER_RIOT_ID`            | `Mistyck#Lan`      | Your Riot ID for personal tracking             |
| `LCU_PATH`                    | (auto-detected)    | League install directory                       |
| `DB_PATH`                     | `./data/oraclegg.db` | SQLite database path                        |
| `LIVE_CLIENT_POLL_INTERVAL`   | `3`                | Seconds between Live Client API polls          |
| `LCU_POLL_INTERVAL`           | `2`                | Seconds between LCU lockfile checks            |
| `TIP_COOLDOWN_SECONDS`        | `15`               | Minimum seconds between tips                   |
| `MAX_TIPS_PER_MINUTE`         | `4`                | Maximum tips per minute                        |
| `PIPELINE_REGION`             | `na1`              | Region for data collection                     |
| `PIPELINE_PLAYER_SAMPLE_SIZE` | `500`              | Players to sample per pipeline run             |
| `PIPELINE_MATCHES_PER_PLAYER` | `10`               | Matches fetched per player                     |
| `PIPELINE_MIN_SAMPLE_SIZE`    | `30`               | Minimum matches for a build recommendation     |
| `HOST`                        | `127.0.0.1`        | Server bind address                            |
| `PORT`                        | `8000`             | Server port                                    |
