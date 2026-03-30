"""Matchup-specific knowledge base.

Curated champion vs champion advice that can't be derived from stats alone.
Focused on Viego, Riven, Annie and their common matchups.
"""

MATCHUP_TIPS: dict[tuple[str, str], list[str]] = {
    # ═══════════════════════════════════════════════════════════════
    # ANNIE MID
    # ═══════════════════════════════════════════════════════════════
    ("Annie", "Zed"): [
        "Rush Zhonya's. Use it when Zed ults — his ult damage pops on nothing.",
        "Save stun for when he comes out of R shadow. He always appears behind you.",
        "Pre-6 you win every trade. Punish hard before he has kill pressure.",
    ],
    ("Annie", "Yasuo"): [
        "Your Q goes through Wind Wall. Poke with Q freely.",
        "Wait for him to dash onto you, then Tibbers stun. Don't waste ult into wall.",
        "Tabis reduce his auto damage significantly.",
    ],
    ("Annie", "Fizz"): [
        "Play aggressive levels 1-5. After 6 his all-in beats yours if he dodges stun with E.",
        "Hold stun when his E is up. Bait it first, then combo.",
        "Banshee's Veil blocks his ult. Consider 2nd or 3rd item.",
    ],
    ("Annie", "Syndra"): [
        "She outranges you. Use minions to block her Q-E stun.",
        "Flash + Tibbers is your win condition. Wait for her to waste E, then all-in.",
    ],
    ("Annie", "Ahri"): [
        "Dodge her E charm. If it misses, you can all-in with Tibbers.",
        "She can't match your burst if you land stun. Flash R is almost always a kill.",
        "She outroams you with R. Ping missing and shove wave fast.",
    ],
    ("Annie", "Leblanc"): [
        "Her W dash is predictable — stun where she lands.",
        "If she W's forward, she returns to the pad. Drop Tibbers on the pad.",
        "Early Magic Resist (Null-Magic Mantle) reduces her burst a lot.",
    ],
    ("Annie", "Viktor"): [
        "You outburst him hard. Flash Tibbers before he can react.",
        "Don't stand in his E laser path during laning. Walk sideways.",
        "He outscales you. Close the game or roam to get your team ahead.",
    ],
    ("Annie", "Veigar"): [
        "Dodge his cage (E). If you're inside, you lose.",
        "Early game you're stronger. Punish his weak laning with Q poke.",
        "Late game his ult will one-shot you. Build Banshee's.",
    ],
    ("Annie", "Katarina"): [
        "Save stun for her ult. One stun cancels her entire teamfight.",
        "She roams better than you. Shove and follow, or ping your team.",
        "Don't waste Tibbers when she has Shunpo up — she'll just dash out.",
    ],
    ("Annie", "Akali"): [
        "Her shroud doesn't stop your Tibbers AOE. Drop it on her even in shroud.",
        "W stun is AOE — use it to reveal and stun her in shroud.",
        "She wins extended trades with her passive. Short burst trades only.",
    ],
    ("Annie", "Malzahar"): [
        "His passive spell shield blocks one ability. Pop it with Q, then combo.",
        "He outpushes you. Focus on last hitting, don't waste mana on wave.",
        "QSS or Banshee's for his ult. Or just flash it if you see it coming.",
    ],
    ("Annie", "Xerath"): [
        "He outranges you hard. Dodge his Q by sidestepping.",
        "All-in him with Flash Tibbers — he has no escape once you're on him.",
        "If he wastes E stun, he's a free kill with your combo.",
    ],
    ("Annie", "Lux"): [
        "Dodge her Q snare. If it hits, you're dead.",
        "Flash Tibbers through her poke range. She can't handle your burst.",
        "Her shield won't save her from your full combo.",
    ],

    # ═══════════════════════════════════════════════════════════════
    # RIVEN TOP
    # ═══════════════════════════════════════════════════════════════
    ("Riven", "Darius"): [
        "Short trades only. Q-W-auto then E out. Never let him get 5 bleed stacks.",
        "Bait his Q outer edge by walking in and out. If he misses it, all-in.",
        "After 6, you can all-in if you dodge his Q outer edge with your dashes.",
    ],
    ("Riven", "Renekton"): [
        "Respect his empowered W stun. Don't trade when he has 50+ fury.",
        "You outscale hard. Play safe until 2 items, then you win 1v1.",
        "E his W to shield the stun damage, then trade back.",
    ],
    ("Riven", "Malphite"): [
        "You can't kill him after first armor item. Roam mid and bot instead.",
        "Early game before armor, trade aggressively.",
        "Consider Black Cleaver to shred his armor.",
    ],
    ("Riven", "Garen"): [
        "Trade when his Q is on cooldown. Bait it, E back, re-engage.",
        "Don't let him regen with passive. Keep poking to prevent health from coming back.",
        "Short trades. Long trades let him spin to win.",
    ],
    ("Riven", "Fiora"): [
        "She parries your 3rd Q or W. Mix up your combo timing.",
        "Save W stun — if she parries it, she stuns YOU.",
        "Short trades. Her passive vitals win extended fights.",
    ],
    ("Riven", "Jax"): [
        "Bait his E counter-strike, then re-engage when it's down.",
        "You win short trades early. He outscales in 1v1 after 2 items.",
        "Don't auto-attack into his E — your autos are a big part of your damage.",
    ],
    ("Riven", "Mordekaiser"): [
        "Dodge his E pull with your dashes. If he misses E, you can trade.",
        "His ult steals your stats. QSS removes his R — worth buying.",
        "Short trades. His passive does too much in long fights.",
    ],
    ("Riven", "Nasus"): [
        "Freeze the wave and zone him from stacks. If he can't stack, he's useless.",
        "All-in him early and often. He's weak before Sheen.",
        "Close the game fast. If it goes to 30+ min, he outscales.",
    ],
    ("Riven", "Teemo"): [
        "Gap close with E, then W stun before he can blind you.",
        "His blind only blocks autos, not your Q or W damage.",
        "Buy Oracle Lens after 6 to clear shrooms.",
    ],
    ("Riven", "Sett"): [
        "Don't get hit by his W true damage center. Dash to the side.",
        "Short trades. E-W-Q then dash out before he can grab you.",
        "He's stronger in all-ins if you eat his full W. Respect it.",
    ],
    ("Riven", "Camille"): [
        "Trade when her passive shield is down. Wait for the shield to expire.",
        "You can E out of her R cage walls. Use it to escape.",
        "She wins with passive + Q2 true damage. Short trades before Q2.",
    ],
    ("Riven", "Yone"): [
        "Trade when his E is on cooldown. He has no escape without it.",
        "His Q3 knockup is telegraphed. E to dodge it, then all-in.",
        "He outscales. Push your lead early.",
    ],
    ("Riven", "Irelia"): [
        "Avoid fighting in her minion wave — she'll reset Q off dying minions.",
        "If she misses E stun, you win the trade. Punish hard.",
        "Both of you are strong at 1 item. Whoever gets lead first usually wins lane.",
    ],

    # ═══════════════════════════════════════════════════════════════
    # VIEGO JUNGLE
    # ═══════════════════════════════════════════════════════════════
    ("Viego", "LeeSin"): [
        "He wins early skirmishes. Farm and avoid 1v1 until BotRK or Kraken.",
        "Counter-gank rather than forcing your own ganks early.",
        "After 6 you can match him. Possess a tanky champ in fights for survivability.",
    ],
    ("Viego", "Graves"): [
        "He wins early with burst. Don't contest crabs if he's nearby.",
        "Your sustain from passive beats him in extended fights.",
        "Farm to Kraken, then you can duel him.",
    ],
    ("Viego", "Warwick"): [
        "He's stronger 1v1 early due to healing. Don't duel until you have anti-heal.",
        "His W blood trail reveals low-HP targets. Be careful when low in jungle.",
        "Executioner's Calling early shuts down his healing.",
    ],
    ("Viego", "Kindred"): [
        "Contest her marks when you can. Denying marks slows her scaling.",
        "She kites you well. Engage with W stun, not just running at her.",
        "Her ult prevents death — bait it, then burst after it expires.",
    ],
    ("Viego", "Kayn"): [
        "Invade early. You win 1v1 before he gets form.",
        "Track which form he's going. Red Kayn heals a lot — build anti-heal.",
        "Blue Kayn bursts squishies. Peel for your carries in teamfights.",
    ],
    ("Viego", "Elise"): [
        "She's stronger at levels 3-5. Farm safely and avoid early skirmishes.",
        "Counter-gank her. She's squishy — if you get on her, she dies fast.",
        "She falls off hard mid-late. Outscale her.",
    ],
    ("Viego", "Nidalee"): [
        "She invades and pokes. Ward your jungle entrances.",
        "If she misses spear, she loses half her damage. Dodge and engage.",
        "You massively outscale. Don't int early and you win by default.",
    ],
    ("Viego", "Hecarim"): [
        "He runs you down early. Don't fight in river without vision.",
        "Your W stun interrupts his E charge. Time it right.",
        "He's stronger in 5v5 with R. Look for picks instead of teamfights.",
    ],
    ("Viego", "Vi"): [
        "Her ult is point-and-click. You can't dodge it. Build defensively.",
        "W stun her when she Q charges. It cancels the dash.",
        "She falls off late. Outscale and outteamfight her.",
    ],
    ("Viego", "Jarvan IV"): [
        "You can E (mist) through his ult walls. Don't panic.",
        "He ganks better than you early. Track him and counter-gank.",
        "You outscale in 1v1. After 2 items you win duels.",
    ],
    ("Viego", "Amumu"): [
        "Invade him early. He's weak 1v1 pre-6.",
        "His teamfight is way better than yours. Look for picks before 5v5.",
        "He outscales in teamfights. Splitpush or get picks.",
    ],
    ("Viego", "Sejuani"): [
        "You massively outdamage her 1v1. Invade freely.",
        "Her CC chain in teamfights is dangerous. Flank the backline instead.",
        "She's a setup tank. Kill the carry she's peeling for.",
    ],

    # ═══════════════════════════════════════════════════════════════
    # GENERAL (any champ vs these)
    # ═══════════════════════════════════════════════════════════════
    ("*", "Teemo"): [
        "Buy Oracle Lens to clear shrooms. Walk unpredictable paths.",
        "All-in when his blind is on cooldown. Don't auto-trade into blind.",
    ],
    ("*", "Vayne"): [
        "Don't fight near walls — her E stun does massive damage.",
        "She's weak early. Punish before 2+ items.",
        "Group and burst her in teamfights. She struggles against hard CC.",
    ],
    ("*", "Yuumi"): [
        "Focus whoever Yuumi is attached to. Bursting the host forces detach.",
        "Build Grievous Wounds. Yuumi heals a lot.",
    ],
    ("*", "Master Yi"): [
        "Save hard CC for when he engages. One stun and he's dead.",
        "He's weak early. Invade or pressure before he scales.",
        "Don't 1v1 him late game. Group and CC chain him.",
    ],
    ("*", "Kayle"): [
        "Punish her before level 6. She's one of the weakest early champs.",
        "Dive her pre-11. She doesn't have range yet.",
        "If the game goes to 16, she becomes a hypercarry. Close early.",
    ],
    ("*", "Nasus"): [
        "Freeze the wave and deny stacks. A Nasus with no stacks is useless.",
        "Force fights before 25 min. He only gets stronger.",
    ],
}

ROLE_TIPS: dict[str, list[str]] = {
    "TOP": [
        "Track enemy jungler before trading. Ward river at 3:00.",
        "Freeze near your tower if behind. Let them overextend.",
        "TP bot for dragon fights if you have lane priority.",
    ],
    "JUNGLE": [
        "Full clear is almost always better than forcing a bad level 3 gank.",
        "Track the enemy jungler by watching which lanes push.",
        "Gank the lane with CC first — highest success rate.",
    ],
    "MID": [
        "Shove and roam after 6 if you have kill pressure on side lanes.",
        "Control ward in pixel brush for river vision.",
        "Respect fog of war. If you don't see jungler, play safe.",
    ],
    "ADC": [
        "15 CS = 1 kill of gold. Focus CS over kills in lane.",
        "Stay behind support. Don't walk up alone to auto.",
        "In teamfights, hit whoever is closest safely. Don't tunnel the backline.",
    ],
    "SUPPORT": [
        "Ward enemy jungle entrances for your jungler.",
        "Roam mid after a successful bot recall.",
        "Peel for your carry in teamfights if they're the win condition.",
    ],
}


def get_matchup_tips(your_champ: str, enemy_champ: str) -> list[str]:
    tips = MATCHUP_TIPS.get((your_champ, enemy_champ), [])
    if not tips:
        tips = MATCHUP_TIPS.get(("*", enemy_champ), [])
    return tips


def get_role_tips(role: str) -> list[str]:
    return ROLE_TIPS.get(role, [])
