# Riot Games API Research

Last updated: 2026-03-28

---

## 1. Available APIs & Endpoints

### Riot Developer Portal APIs (Remote / Server-Side)

All requests go to `https://{platform}.api.riotgames.com` (platform routing) or `https://{region}.api.riotgames.com` (regional routing). Auth via `X-Riot-Token` header.

| API | Key Endpoints | What You Get |
|-----|--------------|--------------|
| **Account-V1** | `/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}` | PUUID, gameName, tagLine. Cross-game identity. Regional routing. |
| **Summoner-V4** | `/lol/summoner/v4/summoners/by-puuid/{puuid}` | Summoner ID, account ID, profile icon, summoner level. Platform routing. |
| **Match-V5** | `/lol/match/v5/matches/by-puuid/{puuid}/ids`, `/lol/match/v5/matches/{matchId}`, `/lol/match/v5/matches/{matchId}/timeline` | Match history list, full match details (all 10 players' stats, items, runes, spells, KDA, damage, gold, CS, vision, etc.), minute-by-minute timeline with events. **Regional routing.** |
| **Spectator-V5** | `/lol/spectator/v5/active-games/by-summoner/{puuid}`, `/lol/spectator/v5/featured-games` | Current active game info: both teams' champions, summoner spells, runes/perks, bans. Does NOT include in-game stats (CS, KDA, gold, items). Platform routing. |
| **Champion-Mastery-V4** | `/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}` | Mastery level, points, last play time per champion. |
| **League-V4** | `/lol/league/v4/entries/by-summoner/{summonerId}` | Ranked tier, division, LP, wins/losses, hot streak, etc. |
| **League-Exp-V4** | `/lol/league-exp/v4/entries/{queue}/{tier}/{division}` | Paginated lists of ranked entries. Good for leaderboard crawling. |
| **Champion-V3** | `/lol/platform/v3/champion-rotations` | Free champion rotation list. |
| **Clash-V1** | Multiple endpoints | Tournament data, team info, player registrations. |
| **LOL-Challenges-V1** | Multiple endpoints | Challenge progression, percentiles, leaderboards. |
| **LOL-Status-V4** | `/lol/status/v4/platform-data` | Server status, incidents, maintenance notices. |
| **Tournament-V5** | Multiple endpoints | Tournament creation and management (requires special access). |

### Live Client Data API (Local / In-Game Only)

Runs on `https://127.0.0.1:2999` while a game is active. **No API key needed.** Only works on the machine running the game client.

| Endpoint | Data |
|----------|------|
| `/liveclientdata/allgamedata` | Everything below in one call |
| `/liveclientdata/activeplayer` | Active player's full stats: level, gold, abilities (with levels), runes, summoner spells, current stats (AD, AP, armor, MR, etc.) |
| `/liveclientdata/activeplayername` | Just the player's name |
| `/liveclientdata/activeplayerabilities` | Active player's ability details and levels (Q/W/E/R) |
| `/liveclientdata/activeplayerrunes` | Active player's full rune page |
| `/liveclientdata/playerlist` | All 10 players: champion, team, skin, summoner spells, runes, items, scores (kills/deaths/assists/CS), level |
| `/liveclientdata/playerlist?teamID=ORDER` or `CHAOS` | Filter by team |
| `/liveclientdata/playeritems?summonerName={name}` | Specific player's items |
| `/liveclientdata/playermainrunes?summonerName={name}` | Specific player's keystone rune |
| `/liveclientdata/playerscores?summonerName={name}` | Specific player's KDA and CS |
| `/liveclientdata/playersummonerspells?summonerName={name}` | Specific player's summoner spells |
| `/liveclientdata/gamestats` | Game time, game mode, map |
| `/liveclientdata/eventdata` | Game events (kills, dragons, barons, turrets, etc.) |

**Critical caveat:** This API is officially described as "not supported for use with third party applications" and Riot provides no guarantees of uptime, documentation completeness, or change communication. However, many approved apps (Blitz, Porofessor) use it.

### League Client Update (LCU) API (Local / Client Running)

Runs on a random port on localhost while the League client is open. Requires reading a lockfile for auth credentials. Provides access to the full client state.

| Key Endpoint | Data |
|-------------|------|
| `/lol-champ-select/v1/session` | Champion select state: picks, bans, team composition, player actions |
| `/lol-lobby/v2/lobby` | Lobby state |
| `/lol-summoner/v1/current-summoner` | Current logged-in summoner info |
| Various `/lol-*` paths | Hundreds of internal endpoints |

**This is the only way to get champion select data.** The public Riot API and Spectator API are unaware of games until after champion select completes.

---

## 2. Authentication & Rate Limits

### API Key Types

| Type | Rate Limit | Expiry | Use Case |
|------|-----------|--------|----------|
| **Development** | 20 requests/sec, 100 requests/2 min | 24 hours (auto-refresh if within 1 hour of expiry) | Prototyping, testing. Cannot run a public product. |
| **Personal** | Higher than dev (varies) | Does not expire | Small private tools, personal projects. No approval process needed but must register. |
| **Production** | Much higher (negotiable) | Does not expire | Public-facing products. Requires approval process. |

### Rate Limiting Details

- Rate limits are enforced **per API key** and **per method/region combination**
- Responses include rate limit headers: `X-App-Rate-Limit`, `X-Method-Rate-Limit`, `X-App-Rate-Limit-Count`, `X-Method-Rate-Limit-Count`
- If you exceed limits, you get a `429 Too Many Requests` with a `Retry-After` header
- Both application-level and method-level rate limits apply simultaneously
- Riot can throttle or revoke keys that abuse the system

### Production Key Approval Process

1. Register a product on the Developer Portal
2. Submit a working prototype (not just an idea)
3. Include a website with screenshots describing your product
4. Riot DevRel reviews (~20 business days, can vary)
5. They evaluate: Does it benefit players? Does it help them improve? Does it violate policies? Is it quality?
6. They explicitly do NOT want tools that "solve games" or "make everything too simple"

---

## 3. Live Game Data Deep Dive

### What You Can Get During a Live Game

**Via Spectator-V5 (Remote API, anyone can query):**
- Both teams' champion picks
- Summoner spells for all players
- Rune/perk selections for all players
- Banned champions
- Game mode, map, queue type
- Encrypted summoner IDs (to look up rank, match history, etc.)
- **NOT available:** Items, gold, CS, KDA, abilities, any in-game state

**Via Live Client Data API (Local, player's own machine):**
- ALL players' items (real-time updates)
- ALL players' scores (kills, deaths, assists, CS)
- ALL players' levels
- ALL players' summoner spells and runes
- Active player's detailed stats (AD, AP, armor, MR, ability haste, etc.)
- Active player's ability levels
- Game events (kills, objectives)
- Game timer
- **NOT available for enemies:** Detailed stat breakdowns (AD/AP/etc.), ability levels, cooldowns, exact gold amounts

**Via LCU (Local, champion select phase):**
- Your team's picks and bans as they happen
- Enemy team's picks and bans as they happen (visible ones)
- Hover intentions
- Summoner spell selections
- Player identities (summoner names for lookup)

### Combining APIs for Maximum Data During a Game

1. **Pre-game (champ select):** LCU gives you both teams' picks/bans. Use summoner names to query the remote API for each player's rank, match history, champion mastery, and win rates.
2. **In-game:** Live Client Data API gives you real-time items, scores, and events. Spectator-V5 can supplement with game metadata.
3. **Post-game:** Match-V5 gives you the complete picture with full timeline data.

---

## 4. Static Data Resources

### Data Dragon (Official - Riot)

- URL pattern: `https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/{file}.json`
- Version list: `https://ddragon.leagueoflegends.com/api/versions.json`
- **Champions:** `champion.json` (summary), `champion/{championName}.json` (detailed)
- **Items:** `item.json`
- **Runes:** `runesReforged.json`
- **Summoner Spells:** `summoner.json`
- **Profile Icons:** `profileicon.json`
- **Images:** `https://ddragon.leagueoflegends.com/cdn/{version}/img/{type}/{filename}`

**Known issues:**
- Champion ability data is often inaccurate (wrong numbers, unparsable descriptions)
- Item stats can be incorrect
- Updates lag behind patches (sometimes 1-2 days after a patch)
- Manual update process by Riot

### Community Dragon (Community-Maintained)

- URL: `https://raw.communitydragon.org/latest/`
- Extracts data directly from game files
- More complete than Data Dragon (includes assets DDragon doesn't have)
- Better for: skin data, TFT data, client assets, audio files

### Meraki Analytics (Community - Most Accurate)

- Champion data: `https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json`
- Individual: `https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions/{championName}.json`
- **Most accurate champion stats and ability data available**
- Curated and verified by the community
- Best choice for item and champion stat recommendations

### Recommended Strategy for Your Tool

| Data Need | Best Source |
|-----------|-----------|
| Champion images/icons | Data Dragon |
| Item images/icons | Data Dragon |
| Accurate champion stats/abilities | Meraki Analytics |
| Accurate item stats | Meraki Analytics |
| Champion ID to name mapping | Data Dragon |
| Rune data | Data Dragon |
| Obscure assets (skins, audio, etc.) | Community Dragon |

---

## 5. Limitations & Policy Restrictions

### What You CANNOT Do (Terms of Service)

1. **No previously-unknown game-session information.** You cannot show players data they couldn't already see in the game client. This means:
   - You CANNOT track enemy ultimate cooldowns
   - You CANNOT reveal fog-of-war information
   - You CANNOT show enemy ability levels they haven't used visibly

2. **No decision-making for players.** Your tool cannot dictate what players should do (e.g., "use your ult now", "flash here"). Recommendations and suggestions are a gray area -- showing build suggestions is fine (Blitz/Porofessor do this), but real-time tactical commands are not.

3. **No memory reading.** Tools must not read game memory. Vanguard (Riot's anti-cheat) will block this.

4. **No competitive edge from hidden data.** You cannot surface information not present in the game client to give an advantage.

5. **No disruption of the game.** Cannot interfere with game files, network traffic, or client behavior.

### What You CAN Do (Based on Approved Apps Like Blitz, Porofessor, OP.GG)

1. **Pre-game overlays showing:**
   - Both teams' rank, win rates, recent performance
   - Champion-specific stats (player's win rate on that champion)
   - Match history analysis
   - Suggested builds (items, runes, summoner spells) based on historical data
   - Lane matchup win rates

2. **In-game overlays showing:**
   - Jungle and objective timers (based on visible events)
   - Team gold difference (from Live Client Data API)
   - CS tracking graphs
   - Ward placement stats
   - Build path recommendations (static, not reactive to hidden enemy data)

3. **Post-game analysis:**
   - Full match breakdown
   - Performance trends
   - Improvement suggestions

### Technical Limitations

| Limitation | Impact |
|-----------|--------|
| No champ select data from remote API | Must use LCU (local client only) for pre-game data |
| Spectator API has no in-game stats | Use Live Client Data API instead (local only) |
| Live Client Data API is "unsupported" | Could break without notice |
| Development key expires every 24 hours | Unusable for any persistent product |
| Production key requires working prototype | Chicken-and-egg: need to build before getting approved |
| Rate limits on dev key (20/sec, 100/2min) | Throttles development significantly when crawling data |
| Data Dragon accuracy issues | Use Meraki Analytics for champion/item stats |
| Match-V5 requires PUUID (not summoner name) | Must chain: Riot ID -> Account-V1 -> PUUID -> Match-V5 |

### Monetization Rules

- Products CAN be monetized if registered and approved/acknowledged on the Developer Portal
- There MUST be a free tier of access for players
- Advertising is allowed in the free tier
- Cannot sell Riot's data directly

---

## 6. Architecture Implications for OracleGG

### Recommended API Strategy

```
Phase 1 (Development):
  - Use Dev API key (rotate every 24 hours)
  - Build with Live Client Data API + LCU for local overlays
  - Use Data Dragon + Meraki for static data
  - Use Match-V5 for historical analysis features

Phase 2 (Personal Key):
  - Register as personal app
  - Get persistent key with modest rate limits
  - Good enough for private/small-community use

Phase 3 (Production):
  - Submit for production approval with working product
  - Get higher rate limits
  - Required for any public-facing product
```

### Data Flow for a Recommendation/Overlay Tool

```
Champion Select:
  LCU (/lol-champ-select/v1/session)
    -> Get both teams' picks
    -> Query Account-V1 + Summoner-V4 for player identities
    -> Query League-V4 for ranks
    -> Query Match-V5 for recent match history
    -> Query Champion-Mastery-V4 for mastery data
    -> Cross-reference with Meraki for champion stats
    -> Generate recommendations (builds, runes, matchup tips)

In-Game:
  Live Client Data API (localhost:2999)
    -> Poll /liveclientdata/allgamedata every few seconds
    -> Track items, scores, events in real-time
    -> Update recommendations based on game state
    -> Show objective timers based on event data

Post-Game:
  Match-V5 (/lol/match/v5/matches/{matchId})
    -> Full match analysis with timeline
    -> Performance metrics
    -> Historical trend tracking
```

### Key Risks

1. **Live Client Data API instability** - Riot considers this unsupported. It could change or break without notice. Every approved app that uses it accepts this risk.
2. **Policy enforcement ambiguity** - The line between "recommendation" and "dictating decisions" is subjective. Apps like Blitz show build suggestions and are approved, so this appears safe.
3. **Production key approval uncertainty** - Riot explicitly says they don't want tools that "solve games." Your pitch needs to emphasize player learning/improvement, not "win more."
4. **LCU dependency** - Champion select data requires the local client. There's no remote API alternative. Your tool must run on the player's machine.

---

## Sources

- [Riot Developer Portal - APIs](https://developer.riotgames.com/apis)
- [Riot Developer Portal - Data Dragon / LoL Docs](https://developer.riotgames.com/docs/lol)
- [Riot Developer Portal - Rate Limiting](https://developer.riotgames.com/docs/portal)
- [Riot Developer Portal - General Policies](https://developer.riotgames.com/policies/general)
- [Riot Developer Portal - Game-Specific Policies](https://developer.riotgames.com/policies/game-specific)
- [Riot Developer Portal - API Terms and Conditions](https://developer.riotgames.com/terms)
- [Riot API Community Documentation](https://riot-api-libraries.readthedocs.io/)
- [Riot API Community - Data Dragon](https://riot-api-libraries.readthedocs.io/en/latest/ddragon.html)
- [Riot API Community - LCU](https://riot-api-libraries.readthedocs.io/en/latest/lcu.html)
- [Production Key Applications](https://support-developer.riotgames.com/hc/en-us/articles/22801383038867-Production-Key-Applications)
- [Third Party Applications Policy](https://support-leagueoflegends.riotgames.com/hc/en-us/articles/225266848-Third-Party-Applications)
- [Vanguard FAQ for Third Party Applications](https://www.riotgames.com/en/DevRel/vanguard-faq)
- [Overwolf Riot Games Compliance](https://dev.overwolf.com/ow-native/guides/game-compliance/riot-games/)
- [Meraki Analytics - lolstaticdata](https://github.com/meraki-analytics/lolstaticdata)
- [HextechDocs - Getting Started](https://hextechdocs.dev/getting-started-with-the-riot-games-api/)
- [HextechDocs - Data Dragon](https://hextechdocs.dev/data-dragon/)
- [Spectator-V4 Blog (DarkIntaqt)](https://darkintaqt.com/blog/spectator-v4)
- [LCU Champ Select Session Gist](https://gist.github.com/xadamxk/8cb5d21d24bb78d63c5241e97087bb23)
- [Best LoL Companion Apps 2026 (iTero)](https://www.itero.gg/articles/what-is-the-best-league-of-legends-companion-app-in-2025)
