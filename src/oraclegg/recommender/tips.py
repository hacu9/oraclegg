"""In-game tip engine.

Analyzes live game state and generates actionable coaching tips.
"""

from dataclasses import dataclass, field
from time import time

SUMMONER_SPELL_NAMES = {
    1: "Cleanse", 3: "Exhaust", 4: "Flash", 6: "Ghost", 7: "Heal",
    11: "Smite", 12: "Teleport", 14: "Ignite", 21: "Barrier",
}

# Items that are power spikes worth calling out
POWER_SPIKE_ITEMS = {
    3031: ("Infinity Edge", "massive crit spike, avoid extended trades"),
    3089: ("Rabadon's Deathcap", "huge AP spike, respect burst damage"),
    6672: ("Kraken Slayer", "strong DPS item, don't let them auto freely"),
    3124: ("Guinsoo's Rageblade", "on-hit spike, short trades are better"),
    6333: ("Death's Dance", "harder to burst, focus someone else or CC chain"),
    3065: ("Spirit Visage", "increased healing, consider anti-heal"),
    3075: ("Thornmail", "has Grievous Wounds, don't rely on healing vs them"),
    3076: ("Bramble Vest", "has Grievous Wounds on autos"),
    3033: ("Mortal Reminder", "they have anti-heal, healing is reduced"),
    3036: ("Lord Dominik's Regards", "armor pen spike, tanks beware"),
    3135: ("Void Staff", "magic pen spike, MR is less effective"),
    6676: ("The Collector", "execute threshold, don't fight low HP"),
    3157: ("Zhonya's Hourglass", "can stasis, bait it before committing"),
    3026: ("Guardian Angel", "has revive, focus others or bait GA first"),
    6631: ("Stridebreaker", "has a slow active, harder to kite"),
    3078: ("Trinity Force", "strong dueling spike"),
    6692: ("Eclipse", "shield on proc + armor pen, short trades hurt"),
    6653: ("Liandry's Torment", "burn damage, don't stay in extended fights low HP"),
    6673: ("Immortal Shieldbow", "lifeline shield when low, burst through it or back off"),
    4645: ("Shadowflame", "strong AP burst, respect one-shot potential"),
    4646: ("Stormsurge", "burst + MS on kill, don't clump"),
    3152: ("Hextech Rocketbelt", "dash + burst, watch for gap close"),
    6610: ("Sundered Sky", "heals on first hit, avoid short trades"),
}

# Anti-heal items
ANTIHEAL_ITEMS = {3075, 3076, 3033, 3165, 3916}

# Armor items
ARMOR_ITEMS = {3075, 3076, 3047, 3143, 3110, 3068, 3742}

# MR items
MR_ITEMS = {3065, 3111, 3194, 3155, 3156, 3190}

# Heavy healing champions
HEALING_CHAMPS = {
    "Aatrox", "Warwick", "Sylas", "Vladimir", "Soraka", "Yuumi",
    "DrMundo", "Fiora", "Irelia", "Swain", "Illaoi", "Briar",
}


@dataclass
class Tip:
    priority: int  # 0=urgent, 1=important, 2=info
    category: str  # "item", "objective", "threat", "strategy", "build"
    message: str
    timestamp: float = field(default_factory=time)


class TipEngine:
    def __init__(self):
        self._seen_items: dict[str, set[int]] = {}  # player_name -> set of item IDs already alerted
        self._last_tips: list[str] = []
        self._last_tip_time: float = 0
        self._tip_cooldown = 8  # seconds between tips
        self._game_tips_given: set[str] = set()  # dedup key for one-time tips

    def analyze(self, game_state: dict) -> list[Tip]:
        """Analyze game state and return prioritized tips."""
        tips = []

        players = game_state.get("players", [])
        active_player = game_state.get("active_player", {})
        game_time = game_state.get("game_time", 0)
        events = game_state.get("events", [])

        if not players or not active_player:
            return tips

        my_name = active_player.get("name", "")

        # Find my player and team
        me = None
        my_team = ""
        for p in players:
            if p.get("riotIdGameName", p.get("summonerName", "")) == my_name:
                me = p
                my_team = p.get("team", "")
                break

        if not me:
            return tips

        allies = [p for p in players if p.get("team") == my_team]
        enemies = [p for p in players if p.get("team") != my_team]

        # Run all analysis
        tips.extend(self._check_enemy_items(enemies, me, game_time))
        tips.extend(self._check_threats(enemies, allies, game_time))
        tips.extend(self._check_team_gold(allies, enemies, game_time))
        tips.extend(self._check_build_advice(me, enemies, game_time))
        tips.extend(self._check_dead_enemies(enemies, game_time))
        tips.extend(self._check_power_spikes(me, enemies, game_time))
        tips.extend(self._check_comp_advice(enemies, me, game_time))
        tips.extend(self._check_objectives(game_time))
        tips.extend(self._check_tempo(allies, enemies, game_time))
        tips.extend(self._check_strategy(allies, enemies, game_time))
        tips.extend(self._check_boots(me, enemies, game_time))
        tips.extend(self._check_dragon(allies, enemies, game_state))
        tips.extend(self._check_matchup_kb(me, enemies))

        # Sort by priority, dedup
        tips.sort(key=lambda t: t.priority)

        # Filter out already-given one-time tips
        # Use first 30 chars of message as dedup key (catches "Team is far behind" variants)
        filtered = []
        for t in tips:
            key = f"{t.category}:{t.message[:30]}"
            if key not in self._game_tips_given:
                filtered.append(t)
                self._game_tips_given.add(key)

        return filtered[:5]  # Max 5 tips per poll

    def _get_player_items(self, player: dict) -> list[dict]:
        return [i for i in player.get("items", []) if i.get("itemID", 0) > 0]

    def _get_player_item_ids(self, player: dict) -> set[int]:
        return {i["itemID"] for i in self._get_player_items(player)}

    def _check_enemy_items(self, enemies: list, me: dict, game_time: float) -> list[Tip]:
        tips = []
        from oraclegg.recommender.rules.item_triggers import ITEM_TRIGGER_MAP

        for enemy in enemies:
            champ = enemy.get("championName", "")
            player_key = enemy.get("riotIdGameName", champ) or champ
            items = self._get_player_item_ids(enemy)

            if player_key not in self._seen_items:
                self._seen_items[player_key] = set()

            new_items = items - self._seen_items[player_key]
            self._seen_items[player_key] = items

            for item_id in new_items:
                if item_id in ITEM_TRIGGER_MAP:
                    item_name, advice, prio = ITEM_TRIGGER_MAP[item_id]
                    tips.append(Tip(
                        priority=prio,
                        category="item",
                        message=f"{champ} completed {item_name} — {advice}",
                    ))
                elif item_id in POWER_SPIKE_ITEMS:
                    item_name, advice = POWER_SPIKE_ITEMS[item_id]
                    tips.append(Tip(
                        priority=1,
                        category="item",
                        message=f"{champ} completed {item_name} — {advice}",
                    ))
        return tips

    def _check_threats(self, enemies: list, allies: list, game_time: float) -> list[Tip]:
        tips = []
        for enemy in enemies:
            champ = enemy.get("championName", "")
            scores = enemy.get("scores", {})
            kills = scores.get("kills", 0)
            deaths = scores.get("deaths", 0)

            # Super fed enemy
            if kills >= 10 and deaths <= 3:
                key = f"superfed_{champ}"
                if key not in self._game_tips_given:
                    self._game_tips_given.add(key)
                    tips.append(Tip(
                        priority=0,
                        category="threat",
                        message=f"{champ} is {kills}/{deaths} — DO NOT fight them alone. Group up or avoid.",
                    ))

            # Fed enemy with specific champion advice
            if kills >= 6 and deaths <= 3:
                if champ in HEALING_CHAMPS:
                    key = f"healing_threat_{champ}"
                    if key not in self._game_tips_given:
                        self._game_tips_given.add(key)
                        # Check if team has anti-heal
                        team_has_antiheal = False
                        for ally in allies:
                            if self._get_player_item_ids(ally) & ANTIHEAL_ITEMS:
                                team_has_antiheal = True
                                break
                        if not team_has_antiheal:
                            tips.append(Tip(
                                priority=0,
                                category="build",
                                message=f"{champ} is fed and heals a lot — your team needs anti-heal (Mortal Reminder / Morellonomicon)!",
                            ))
        return tips

    def _check_team_gold(self, allies: list, enemies: list, game_time: float) -> list[Tip]:
        tips = []

        ally_kills = sum(p.get("scores", {}).get("kills", 0) for p in allies)
        ally_deaths = sum(p.get("scores", {}).get("deaths", 0) for p in allies)
        enemy_kills = sum(p.get("scores", {}).get("kills", 0) for p in enemies)
        enemy_deaths = sum(p.get("scores", {}).get("deaths", 0) for p in enemies)

        kill_diff = ally_kills - enemy_kills

        if kill_diff <= -10:
            tips.append(Tip(
                priority=0,
                category="strategy",
                message=f"Team is far behind ({ally_kills} vs {enemy_kills} kills). Play safe, farm, look for picks — don't force 5v5.",
            ))
        elif kill_diff <= -5:
            tips.append(Tip(
                priority=1,
                category="strategy",
                message=f"Behind in kills ({ally_kills} vs {enemy_kills}). Focus on farming and objectives, avoid risky fights.",
            ))
        elif kill_diff >= 10:
            tips.append(Tip(
                priority=2,
                category="strategy",
                message=f"Team is stomping ({ally_kills} vs {enemy_kills}). Force objectives, don't throw by chasing kills.",
            ))
        elif kill_diff >= 5 and game_time > 1200:
            tips.append(Tip(
                priority=2,
                category="strategy",
                message=f"Ahead in kills. Push your lead — take Baron or inhibitor towers.",
            ))

        return tips

    def _check_build_advice(self, me: dict, enemies: list, game_time: float) -> list[Tip]:
        tips = []
        my_items = self._get_player_item_ids(me)
        my_champ = me.get("championName", "")

        # Count enemy damage types
        enemy_ap = 0
        enemy_ad = 0
        for e in enemies:
            champ = e.get("championName", "")
            items = self._get_player_item_ids(e)
            # Check for AP items
            if items & {3089, 4645, 4646, 6653, 6655, 3152, 3115, 3116}:
                enemy_ap += 1
            # Check for AD items
            if items & {3031, 6672, 6676, 3036, 6333, 6692, 3078, 6631}:
                enemy_ad += 1

        # Suggest MR if heavy AP and you have none
        if enemy_ap >= 3 and not (my_items & MR_ITEMS):
            tips.append(Tip(
                priority=1,
                category="build",
                message=f"Enemy has {enemy_ap} AP threats — consider building MR (Mercury's Treads, Maw of Malmortius, or Spirit Visage).",
            ))

        # Suggest Armor if heavy AD and you have none
        if enemy_ad >= 3 and not (my_items & ARMOR_ITEMS):
            tips.append(Tip(
                priority=1,
                category="build",
                message=f"Enemy has {enemy_ad} AD threats — consider Plated Steelcaps, Death's Dance, or Randuin's Omen.",
            ))

        # Check if enemies have healing and we don't have anti-heal
        healing_enemies = [e for e in enemies if e.get("championName", "") in HEALING_CHAMPS]
        if healing_enemies and not (my_items & ANTIHEAL_ITEMS):
            names = ", ".join(e.get("championName", "") for e in healing_enemies)
            tips.append(Tip(
                priority=1,
                category="build",
                message=f"Enemy has heavy healing ({names}) — build Grievous Wounds (Executioner's / Oblivion Orb).",
            ))

        return tips

    def _check_dead_enemies(self, enemies: list, game_time: float) -> list[Tip]:
        tips = []
        dead_enemies = [e for e in enemies if e.get("isDead", False)]

        if len(dead_enemies) >= 3 and game_time > 1200:
            names = ", ".join(e.get("championName", "") for e in dead_enemies)
            tips.append(Tip(
                priority=0,
                category="objective",
                message=f"{len(dead_enemies)} enemies dead ({names}) — push for Baron or towers NOW!",
            ))
        elif len(dead_enemies) >= 2 and game_time > 900:
            tips.append(Tip(
                priority=1,
                category="objective",
                message=f"{len(dead_enemies)} enemies dead — look for dragon, baron, or tower push.",
            ))

        return tips

    def _check_power_spikes(self, me: dict, enemies: list, game_time: float) -> list[Tip]:
        tips = []
        my_level = me.get("level", 0)

        # Level 6 spike
        for enemy in enemies:
            e_level = enemy.get("level", 0)
            champ = enemy.get("championName", "")

            if e_level == 6 and my_level < 6:
                tips.append(Tip(
                    priority=1,
                    category="threat",
                    message=f"{champ} just hit level 6 before you — play safe until you also have your ult.",
                ))

        return tips

    def _check_comp_advice(self, enemies: list, me: dict, game_time: float) -> list[Tip]:
        tips = []

        # Count enemy CC (tanks/supports usually have CC)
        tank_count = 0
        for e in enemies:
            items = self._get_player_item_ids(e)
            if items & {3075, 3143, 3110, 3065, 3068, 3742, 3190}:
                tank_count += 1

        if tank_count >= 3:
            my_items = self._get_player_item_ids(me)
            has_pen = bool(my_items & {3036, 3135, 3033})
            if not has_pen:
                tips.append(Tip(
                    priority=1,
                    category="build",
                    message=f"Enemy has {tank_count} tanky champions — you need armor/magic penetration to deal damage.",
                ))

        return tips


    def _check_matchup_kb(self, me: dict, enemies: list) -> list[Tip]:
        """Fire matchup-specific tips from knowledge base (once per game)."""
        key = "matchup_kb"
        if key in self._game_tips_given:
            return []

        from oraclegg.recommender.matchup_kb import get_matchup_tips
        my_champ = me.get("championName", "")
        tips = []
        for enemy in enemies:
            try:
                e_champ = enemy.get("championName", "")
                matchup_tips = get_matchup_tips(my_champ, e_champ)
                if matchup_tips:
                    tips.append(Tip(
                        priority=1,
                        category="strategy",
                        message=f"vs {e_champ}: {matchup_tips[0]}",
                    ))
            except Exception:
                pass

        self._game_tips_given.add(key)  # Mark after loop completes
        return tips[:3]

    def _check_dragon(self, allies: list, enemies: list, game_state: dict) -> list[Tip]:
        """Auto-evaluate dragon when rift transforms."""
        terrain = game_state.get("map_terrain", "Default")
        if terrain == "Default":
            return []

        key = f"dragon_eval_{terrain}"
        if key in self._game_tips_given:
            return []
        self._game_tips_given.add(key)

        from oraclegg.recommender.rules.dragon_rules import evaluate_dragon
        ally_champs = [p.get("championName", "") for p in allies]
        enemy_champs = [p.get("championName", "") for p in enemies]
        d = evaluate_dragon(terrain, ally_champs, enemy_champs)

        prio = 0 if d["priority"] == "high" else 1 if d["priority"] == "medium" else 2
        return [Tip(
            priority=prio,
            category="objective",
            message=f"{terrain} Dragon soul — {d['contest']}. {d['reasons'][0] if d['reasons'] else ''}",
        )]

    def _check_boots(self, me: dict, enemies: list, game_time: float) -> list[Tip]:
        """Recommend boots based on enemy comp. Fires once early-mid game."""
        key = "boot_recommendation"
        if key in self._game_tips_given:
            return []
        # Only suggest boots between 3-12 minutes (when you'd normally buy them)
        if game_time < 180 or game_time > 720:
            return []

        # Check if we already have completed boots
        my_items = self._get_player_item_ids(me)
        boot_ids = {3006, 3009, 3020, 3047, 3111, 3117, 3158}
        if my_items & boot_ids:
            self._game_tips_given.add(key)
            return []

        from oraclegg.recommender.rules.boots_rules import recommend_boots
        my_champ = me.get("championName", "")
        my_role = ""
        # Infer role from position if available
        for r in ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]:
            if me.get("position", "").upper() == r:
                my_role = r
                break
        if not my_role:
            my_role = "MID"  # Default

        enemy_champs = [e.get("championName", "") for e in enemies]
        enemy_items = {
            e.get("championName", ""): self._get_player_item_ids(e)
            for e in enemies
        }

        rec = recommend_boots(my_champ, my_role, enemy_champs, enemy_items)
        self._game_tips_given.add(key)

        reason = rec["reasons"][0] if rec["reasons"] else "Best option for this matchup"
        return [Tip(
            priority=1,
            category="build",
            message=f"Recommended boots: {rec['boot_name']} — {reason}",
        )]

    def _check_strategy(self, allies: list, enemies: list, game_time: float) -> list[Tip]:
        from oraclegg.recommender.rules.power_spike_rules import analyze_team_strategy
        ally_champs = [p.get("championName", "") for p in allies]
        enemy_champs = [p.get("championName", "") for p in enemies]
        results = analyze_team_strategy(ally_champs, enemy_champs, game_time, self._game_tips_given)
        return [Tip(priority=p, category=c, message=m) for p, c, m in results]

    def _check_objectives(self, game_time: float) -> list[Tip]:
        from oraclegg.recommender.rules.objective_rules import check_objective_timers
        results = check_objective_timers(game_time, self._game_tips_given)
        return [Tip(priority=p, category=c, message=m) for p, c, m in results]

    def _check_tempo(self, allies: list, enemies: list, game_time: float) -> list[Tip]:
        from oraclegg.recommender.rules.gold_lead_rules import check_game_tempo
        ally_kills = sum(p.get("scores", {}).get("kills", 0) for p in allies)
        enemy_kills = sum(p.get("scores", {}).get("kills", 0) for p in enemies)
        results = check_game_tempo(ally_kills, enemy_kills, game_time, self._game_tips_given)
        return [Tip(priority=p, category=c, message=m) for p, c, m in results]


# Global instance
tip_engine = TipEngine()
