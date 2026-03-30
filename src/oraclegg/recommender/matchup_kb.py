"""Matchup-specific knowledge base.

Curated champion vs champion advice that can't be derived from stats alone.
Focused on Viego, Riven, Annie and their common matchups.
Updated for Season 2025-2026 (Patch 26.x).
"""

MATCHUP_TIPS: dict[tuple[str, str], list[str]] = {
    # ═══════════════════════════════════════════════════════════════
    # ANNIE MID — ~31 matchups
    # ═══════════════════════════════════════════════════════════════
    ("Annie", "Zed"): [
        "Rush Zhonya's Hourglass. Activate it the instant Zed R lands — his Death Mark pop deals nothing.",
        "Pre-6 you hard-win trades. Zone him with stun threat; if he walks up for CS, Q him.",
        "After 6, save stun for when he appears behind you from R. Tibbers + stun on his R exit is a kill.",
    ],
    ("Annie", "Yasuo"): [
        "Your Q and W are not projectiles for Wind Wall purposes — Q passes through it. Abuse this.",
        "Pop his passive shield with an auto or non-stun Q, then full combo when shield is down.",
        "Flash + Tibbers when he has no passive shield is nearly guaranteed kill at 6.",
    ],
    ("Annie", "Fizz"): [
        "Bully hard levels 1-5. Your auto range and Q poke dominate before he has E + ult.",
        "Post-6, never Tibbers while his E (Playful/Trickster) is up — bait it first, then combo.",
        "Banshee's Veil 2nd or 3rd item blocks his R shark, removing his primary engage.",
    ],
    ("Annie", "Syndra"): [
        "She outranges you significantly. Use minions to block her E stun (Scatter the Weak).",
        "Flash + Tibbers is your only reliable engage. Wait for her to waste E, then all-in.",
        "Rush boots early to dodge her Q poke. Sorcerer's into Malignance is the standard path.",
    ],
    ("Annie", "Ahri"): [
        "Dodge her E charm at all costs — if she misses it, she cannot win an all-in against your burst.",
        "She outroams you with triple R dash. Ping missing instantly and hard-shove wave.",
        "Flash + Tibbers is almost always lethal if charm is on cooldown. Punish her aggression.",
    ],
    ("Annie", "Leblanc"): [
        "Her W dash is predictable — she returns to the pad. Drop Tibbers on the W return pad.",
        "If LeBlanc W's forward aggressively, stun where she lands for a guaranteed combo.",
        "Early Null-Magic Mantle or Verdant Barrier reduces her burst significantly before first item.",
    ],
    ("Annie", "Viktor"): [
        "You hard-outburst Viktor. Flash + Tibbers before he can E + Q trade back.",
        "Don't stand in his E (Death Ray) path. Sidestep it during laning.",
        "He outscales you. Roam to side lanes and force the game closed before 3 items.",
    ],
    ("Annie", "Veigar"): [
        "Dodge his E cage (Event Horizon) — if trapped inside, you lose the trade or die.",
        "Pre-6 you are much stronger. Punish his weak early laning with Q poke on cooldown.",
        "Late game his R one-shots you. Build Banshee's Veil to survive his burst rotation.",
    ],
    ("Annie", "Katarina"): [
        "Hold stun exclusively for her R (Death Lotus). One stun cancels her entire teamfight damage.",
        "Stand away from her daggers on the ground. If she Shunpos to a dagger, instant W stun.",
        "Shove wave fast — if she roams and you can't follow, at least make her lose CS to tower.",
    ],
    ("Annie", "Akali"): [
        "Tibbers AOE damages her inside Twilight Shroud. Drop it on her even when invisible.",
        "W stun is AOE — use it to reveal and stun Akali inside shroud.",
        "She wins extended trades with passive autos. Only take short burst trades: Q-W and walk away.",
    ],
    ("Annie", "Malzahar"): [
        "Pop his passive spell shield with a single auto or non-stun Q, then full combo 1 second later.",
        "He outpushes you with Voidlings + E. Focus on last-hitting; don't waste mana contesting wave.",
        "Buy QSS against his R suppress, or Banshee's to block it entirely.",
    ],
    ("Annie", "Xerath"): [
        "He massively outranges you. Sidestep his Q (Arcanopulse) — it has a clear wind-up animation.",
        "Flash + Tibbers all-in is your only win condition. He has zero mobility once you close the gap.",
        "If he wastes E stun, he's a free kill for your full combo. Track its cooldown carefully.",
    ],
    ("Annie", "Lux"): [
        "Dodge her Q snare (Light Binding). If it hits at close range, her full combo kills you.",
        "Flash + Tibbers through her poke range. She has no escape and can't handle your burst.",
        "Her W shield won't save her from a full stun + Tibbers + Ignite combo.",
    ],
    ("Annie", "Orianna"): [
        "Orianna outranges you and wins poke wars. Stay healthy and look for all-in with Flash R.",
        "Track her ball position. Walk away from it so she can't Q-W-R combo you.",
        "You outburst her at 6. If she wastes Q-W on wave, Flash Tibbers for a kill.",
    ],
    ("Annie", "Cassiopeia"): [
        "Cassiopeia is a hard counter — she outranges, outsustains with E healing, and her R counters yours.",
        "Never face her when she has R (Petrifying Gaze). Flash Tibbers from an angle she isn't facing.",
        "Buy boots early. Her Q (Noxious Blast) grounds you if you step in the poison; dodge it to maintain mobility.",
    ],
    ("Annie", "Ryze"): [
        "You outburst Ryze hard pre-6. Zone him off CS with stun threat — he's weak early.",
        "Flash Tibbers before he can E-Q combo. His shield from combos won't save him from full burst.",
        "He outscales you with items. Close the game early or roam to get your team ahead.",
    ],
    ("Annie", "Twisted Fate"): [
        "You win lane hard. His range is similar to yours, but your burst is far superior.",
        "When he locks Gold Card, back off. After he uses it, all-in while W is on cooldown.",
        "Match his R roams by pushing wave and following. Your Flash Tibbers is stronger in 2v2s.",
    ],
    ("Annie", "Galio"): [
        "Galio's passive MR and W (Shield of Durand) make him tanky against your burst. Extended poke is better.",
        "Don't Flash Tibbers into his W channel — he'll taunt you and waste your combo.",
        "He outroams you with R. Ping missing the second he disappears and hard-shove mid.",
    ],
    ("Annie", "Talon"): [
        "Talon is a hard counter — he jumps walls to roam, and his burst kills you before you can react.",
        "Rush Zhonya's. When he jumps on you with R, Zhonya's wastes his bleed and stealth damage.",
        "Ward raptors entrance. If you see him roaming over a wall, ping immediately.",
    ],
    ("Annie", "Qiyana"): [
        "She dashes and bursts fast. Save stun defensively — W when she E-Q's onto you.",
        "Zhonya's is critical. Her full combo with R can one-shot you; Zhonya's buys time for team.",
        "Pre-6 you have the advantage. Poke her with Q and zone with stun threat.",
    ],
    ("Annie", "Diana"): [
        "Diana is a tough matchup. Her shield and dash let her all-in you while tanking your burst.",
        "Save stun for when she E's (Lunar Rush) in. Stun + Tibbers while she's on top of you.",
        "Build Zhonya's — her R pull + burst can one-shot you. Zhonya's during her R buys time.",
    ],
    ("Annie", "Ekko"): [
        "Respect his level 6 — his R (Chronobreak) undoes your burst. Force his R, then re-engage.",
        "Don't stand on his W (Parallel Convergence) zone. If you see the field, walk out immediately.",
        "Short Q poke wins lane pre-6. He struggles against ranged poke he can't dodge.",
    ],
    ("Annie", "Yone"): [
        "Punish him when he uses E (Soul Unbound) aggressively. Stun him at his E snap-back location.",
        "Your stun hard-counters his Q3 engage. Hold W for when he dashes in with Q3 knockup.",
        "He outscales you. Use your lane dominance to roam and get a lead before he hits 2 items.",
    ],
    ("Annie", "Sylas"): [
        "He steals Tibbers but without your stun passive it's weaker. Don't let him heal with W in trades.",
        "Short Q-W burst trades. Don't let fights last long enough for his W heal to matter.",
        "Build Oblivion Orb early to cut his W healing, which is his main lane sustain.",
    ],
    ("Annie", "Naafiri"): [
        "You counter Naafiri. Your AOE stun + Tibbers kills her and her packmates instantly.",
        "Hold stun for when she W (Hounds' Pursuit) dashes in. Stun-Tibbers combo deletes her.",
        "She roams with R. Shove wave, ping missing, and drop a ward near raptors.",
    ],
    ("Annie", "Hwei"): [
        "Hwei outranges you and pokes hard. His long-range Q combos chunk you before you can engage.",
        "Flash Tibbers is your only reliable engage. Wait for him to step forward to EQ poke, then go.",
        "Build Stormsurge + Shadowflame for maximum burst. You need to one-shot him before he kites.",
    ],
    ("Annie", "Aurora"): [
        "Aurora's R (Between Worlds) traps you in a zone. Save Flash to escape it or Zhonya's inside it.",
        "She kites well with passive empowered autos and Q. All-in with Flash Tibbers when she wastes E dash.",
        "Pre-6 you trade evenly. Post-6 her ult zone controls fights. Don't fight inside her R.",
    ],
    ("Annie", "Neeko"): [
        "Her R (Pop Blossom) is like yours — AOE stun. But you outburst her if you stun first.",
        "Don't get hit by her E root (Tangle-Barbs) through minions. It extends through the wave.",
        "If she disguises as a minion or ally, Tibbers AOE still hits. Use W stun to reveal.",
    ],
    ("Annie", "Ziggs"): [
        "He outranges you hard with Q bounces and E minefield. Dodge Q and walk around mines.",
        "Flash Tibbers is your only engage. He has W (Satchel Charge) to knock you away — bait it first.",
        "Shove and roam. You can't poke him out, but you teamfight better with Flash Tibbers.",
    ],
    ("Annie", "Brand"): [
        "Dodge his W (Pillar of Flame) — it's his primary poke. Sidestep and then Q him back.",
        "If he lands E-Q (Sear stun), he wins the trade. Stay behind minions to block Q.",
        "All-in with Flash Tibbers at 6. Your burst kills him before he can land his full combo.",
    ],
    ("Annie", "Vel'Koz"): [
        "Vel'Koz hard-counters you — he outranges and his R melts you from outside your engage range.",
        "Flash Tibbers is mandatory. If you don't Flash on him, you never reach him.",
        "Dodge his Q (Plasma Fission) geometry — it splits at an angle. Walk unpredictably.",
    ],

    # ═══════════════════════════════════════════════════════════════
    # RIVEN TOP — ~27 matchups
    # ═══════════════════════════════════════════════════════════════
    ("Riven", "Darius"): [
        "Short trades only: Q-W-auto then E out. Never let him stack 5 Hemorrhage bleeds.",
        "Dodge his Q outer ring with your E dash — if he hits inner ring only, you win the trade.",
        "Ignite is mandatory. At 6, all-in if he misses Q edge or wastes E (Apprehend).",
    ],
    ("Riven", "Renekton"): [
        "Respect his empowered W stun when he has 50+ fury. Don't trade into it.",
        "E to shield his W stun damage, then trade back with Q combo while his W is on cooldown.",
        "You outscale hard after 2 items. Play safe early and scale — you win 1v1 after Eclipse + Cleaver.",
    ],
    ("Riven", "Malphite"): [
        "Trade aggressively before his first armor item. After Plated Steelcaps + Bramble, you can't kill him.",
        "Black Cleaver rush is mandatory for armor shred. Eclipse alone won't cut through his armor.",
        "Roam mid and bot. You won't solo-kill a good Malphite, so get your team ahead instead.",
    ],
    ("Riven", "Garen"): [
        "Bait his Q (Decisive Strike) — E away from it, then re-engage when it's on cooldown.",
        "Keep poking him so his passive regen never kicks in (stays in combat).",
        "Short trades only. Long fights let his E (Judgment) spin outdamage you.",
    ],
    ("Riven", "Fiora"): [
        "Delay your W stun — she will Riposte (W) on reaction. Mix up timing: Q3 first, then W later.",
        "If Fiora parries your W, she stuns YOU. This loses you the entire trade or kills you.",
        "Short trades. Her passive vitals win extended fights. Q-W and E out immediately.",
    ],
    ("Riven", "Jax"): [
        "Bait his E (Counter Strike) with Q poke, then E away. Re-engage when it's on cooldown (16s early).",
        "Never auto-attack into his E — your autos and Q damage are blocked. Walk away and wait.",
        "You win short trades early. He outscales in 1v1 after 2 items. Snowball or roam.",
    ],
    ("Riven", "Mordekaiser"): [
        "Dodge his E (Death's Grasp) pull with your E or Q dash. If he misses E, you can trade freely.",
        "QSS removes his R (Realm of Death) — buy it 2nd or 3rd item. He steals your stats inside it.",
        "Short trades. His passive (Darkness Rise) does too much damage in extended fights.",
    ],
    ("Riven", "Nasus"): [
        "Freeze near your tower and zone him from Q stacks. An unstacked Nasus is useless.",
        "All-in early and often. He's incredibly weak before Sheen + level 6.",
        "Close the game before 25 minutes. If he free-farms to 30+ min, he outscales and runs you down.",
    ],
    ("Riven", "Teemo"): [
        "Gap close with E, then W stun before he can Q blind you. Your Q and W damage are not blocked by blind.",
        "His Q blind only blocks auto attacks. Your abilities still deal full damage — combo through it.",
        "Buy Oracle Lens after level 6 to clear mushrooms. Sweeper denies his map control.",
    ],
    ("Riven", "Sett"): [
        "Dash sideways to avoid his W (Haymaker) true-damage center line. Only the center deals true damage.",
        "Short trades: E-W-Q then dash out before he can E (Facebreaker) grab you back in.",
        "Don't fight him when his Grit bar is full. His W punch scales off stored damage.",
    ],
    ("Riven", "Camille"): [
        "Trade when her passive shield (Adaptive Defenses) is down. Wait for the shield to expire before committing.",
        "You can E or Q-dash out of her R (The Hextech Ultimatum) cage walls to escape.",
        "She wins with Q2 (Precision Protocol) true damage. Disengage before her Q2 timer hits.",
    ],
    ("Riven", "Yone"): [
        "Punish when his E (Soul Unbound) is on cooldown — he has no escape without it.",
        "His Q3 knockup is telegraphed by the visual indicator. E-dash sideways to dodge it, then all-in.",
        "You win early levels hard. Push your lead before he hits 2 items and outscales.",
    ],
    ("Riven", "Irelia"): [
        "Never fight inside your own minion wave — she resets Q off dying minions and stacks passive instantly.",
        "If she misses E (Flawless Duet) stun, punish hard. She loses significant DPS without the mark.",
        "Level 1 with full passive stacks she wins. Wait for level 3 with all abilities before trading.",
    ],
    ("Riven", "Aatrox"): [
        "Dash into him to dodge Q sweetspots. His Q1, Q2, Q3 all deal bonus damage at the edge.",
        "Short trade after he uses Q1-Q2, then E out before Q3 (the knockup). Re-engage when Q is on CD.",
        "Executioner's Calling early shuts down his sustain from E and R healing.",
    ],
    ("Riven", "Ornn"): [
        "You can dash through his E (Searing Charge) with your own E to avoid the Brittle proc.",
        "Trade when his W (Bellows Breath) is on cooldown — the Brittle auto-attack is his main damage.",
        "He outscales with item upgrades for the team. Push your early advantage before level 14.",
    ],
    ("Riven", "Gnar"): [
        "Trade when he's Mini Gnar and his rage bar is low. Back off when bar turns orange/red.",
        "In Mini form, his Q boomerang slow is his only peel. Dodge it, then engage with full combo.",
        "Never fight Mega Gnar near walls — his R stun + W deals massive damage.",
    ],
    ("Riven", "Kennen"): [
        "Start Doran's Shield to sustain his poke. Rush Maw of Malmortius — it negates most of his damage.",
        "Watch for his W passive (every 4th auto empowered). Back off when he has it ready.",
        "All-in when his E (Lightning Rush) is on cooldown. Without it he has no escape.",
    ],
    ("Riven", "Jayce"): [
        "Doran's Shield start. He pokes you in ranged form — E to shield his Q (Shock Blast) through gate.",
        "When he swaps to Hammer form, he's melee and you win. Engage after he uses ranged Q+E combo.",
        "Plated Steelcaps reduce his ranged auto harass significantly.",
    ],
    ("Riven", "Volibear"): [
        "His passive (lightning stacks) makes extended trades dangerous. Short Q-W then E out.",
        "Dodge his E (Sky Splitter) zone — it deals % max HP damage and gives him a shield.",
        "Don't fight him under his R (Stormbringer) turret disable. Back off and wait it out.",
    ],
    ("Riven", "Tryndamere"): [
        "Short trades. He wins all-ins with R (Undying Rage) — 5 seconds of immortality.",
        "Bait his R by bursting him, then E away and wait out the 5 seconds before re-engaging.",
        "Freeze near your tower. If he pushes, he's gankable — his only escape is E (Spinning Slash).",
    ],
    ("Riven", "Urgot"): [
        "Dodge his E (Disdain) flip — if he lands it, his passive shotgun knees + W shreds you.",
        "Stay away from his shotgun knee arcs (passive legs). Walk around him, don't circle near him.",
        "At 6, his R executes below 25% HP. Don't fight low — E away and heal up before re-engaging.",
    ],
    ("Riven", "Illaoi"): [
        "Dodge her E (Test of Spirit). If she pulls your soul, walk away from it — don't fight in tentacles.",
        "Never fight her inside her R (Leap of Faith). Dash out, wait for tentacles to expire, then re-engage.",
        "If she misses E, you have a 12-second window to all-in. She's very weak without soul grab.",
    ],
    ("Riven", "Shen"): [
        "Trade through his W (Spirit's Refuge) — your abilities still deal damage. Only autos are blocked.",
        "When he channels R to another lane, hard-shove and take plates. Punish his absence.",
        "You win extended trades. His damage is low — force long fights after his E taunt is down.",
    ],
    ("Riven", "Gragas"): [
        "Dodge his Q barrel — it's his primary poke and slow. Walk around it, don't stand on it.",
        "His E (Body Slam) dash + stun is his engage. E sideways to dodge it, then all-in.",
        "He's deceptively tanky with W (Drunken Rage) damage reduction. Don't commit unless you can burst.",
    ],
    ("Riven", "K'Sante"): [
        "Dodge his W (Path Maker) — he charges then dashes. Sidestep or E through him.",
        "When he R's (All Out) into carry form, he's squishy but deals more damage. Short burst combos win.",
        "He's tanky in base form. Poke with Q and save full combo for when he uses R.",
    ],
    ("Riven", "Ambessa"): [
        "Riven is favored. Your mobility matches hers — use Q dashes to dodge her dash engages.",
        "Punish when her passive (Drakehound) energy is low. She needs it for empowered abilities.",
        "Don't fight inside her R zone. Dash out with E + Q and re-engage when it expires.",
    ],
    ("Riven", "Mundo"): [
        "Early all-ins before he gets Spirit Visage. He's weak pre-6 with no escape.",
        "Executioner's Calling or Ignite to cut his R (Maximum Dosage) regeneration.",
        "Dodge his Q cleavers. They slow you and help him kite. Sidestep then gap-close.",
    ],

    # ═══════════════════════════════════════════════════════════════
    # VIEGO JUNGLE — ~24 matchups
    # ═══════════════════════════════════════════════════════════════
    ("Viego", "Lee Sin"): [
        "He wins early skirmishes hard. Farm efficiently and avoid 1v1 until BotRK or Kraken Slayer.",
        "Counter-gank rather than forcing your own ganks. Track him with deep wards.",
        "After level 8+ you outscale. Possess a tanky champion in teamfights for survivability.",
    ],
    ("Viego", "Graves"): [
        "He wins early with burst and smoke screen. Don't contest first scuttle crab if he's nearby.",
        "Your sustain from passive beats him in extended fights after first item.",
        "Farm to Kraken Slayer. After 1 item you can duel him. Your W stun is key — land it to trade.",
    ],
    ("Viego", "Warwick"): [
        "He outsustains you 1v1 early. Don't duel him until you have anti-heal.",
        "His W blood trail activates on targets below 50% HP. Don't farm jungle while low.",
        "Build Executioner's Calling first back. Shutting down his healing guts his entire kit.",
    ],
    ("Viego", "Kindred"): [
        "Contest her passive marks when you can. Denying marks cripples her scaling.",
        "She kites you well. Open with W (Spectral Maw) stun, don't just run at her.",
        "In teamfights, save Heartbreaker (R) for after her Lamb's Respite (R) expires to execute targets.",
    ],
    ("Viego", "Kayn"): [
        "Invade early — you win 1v1 hard before he gets form. Contest his jungle camps.",
        "Track which form he's building. Red Kayn (Rhaast) heals a lot — build anti-heal items.",
        "Blue Kayn (Shadow Assassin) bursts squishies. Peel for your carries and punish his dive.",
    ],
    ("Viego", "Elise"): [
        "She's stronger at levels 3-5 with cocoon and burst. Avoid early river skirmishes.",
        "Counter-gank her. She's squishy — if you get on her with W stun, she dies fast.",
        "She falls off hard mid-late game. Outscale her by farming efficiently.",
    ],
    ("Viego", "Nidalee"): [
        "She invades and pokes with spears. Ward your jungle entrances and avoid face-checking.",
        "If she misses Q spear, she loses half her burst. Dodge the spear and engage with W.",
        "You massively outscale. Don't die early and you auto-win by 2 items.",
    ],
    ("Viego", "Hecarim"): [
        "He runs you down in early river fights. Don't fight without vision of his pathing.",
        "Your W stun interrupts his E (Devastating Charge). Time it to cancel his engage.",
        "He's stronger in 5v5 with R (Onslaught of Shadows). Look for picks and skirmishes instead.",
    ],
    ("Viego", "Vi"): [
        "Her R (Assault and Battery) is point-and-click CC. You can't dodge it — respect her ult range.",
        "W stun her during her Q (Vault Breaker) charge. It cancels the dash.",
        "She falls off late. You outscale and outteamfight her after 2+ items.",
    ],
    ("Viego", "Jarvan IV"): [
        "You can E (Harrowed Path) through his R (Cataclysm) walls. Don't panic when trapped.",
        "He ganks better than you early. Track his position and counter-gank instead.",
        "You outscale in 1v1 after 2 items. Farm toward your spike and avoid early coin-flips.",
    ],
    ("Viego", "Amumu"): [
        "Invade him early — he's extremely weak 1v1 before level 6 and first item.",
        "His teamfight (R Curse of the Sad Mummy) is far better than yours. Pick fights before 5v5.",
        "In teamfights, don't group tightly. His R is AOE — spread out and flank.",
    ],
    ("Viego", "Sejuani"): [
        "You massively outdamage her 1v1 at all stages. Invade freely and steal camps.",
        "Her CC chain in teamfights is dangerous. Flank the backline instead of going through her.",
        "She's a setup tank — kill the carry she's peeling for, not Sejuani herself.",
    ],
    ("Viego", "Rek'Sai"): [
        "She's stronger early with her tunnel ganks and tremor sense. Avoid contesting her near her tunnels.",
        "Post-6 her R (Void Rush) is a point-and-click burst. Don't get low in 1v1s near her.",
        "You outscale after 1 item. Farm efficiently and you win every duel after Kraken Slayer.",
    ],
    ("Viego", "Kha'Zix"): [
        "Skill matchup. Never fight him when isolated from minions or allies — his Q isolation damage is massive.",
        "Fight near your camps or lane minions to deny his isolation passive.",
        "After 6 his evolved abilities spike hard. Track which ability he evolves and play around it.",
    ],
    ("Viego", "Ekko"): [
        "Burst him to force his R (Chronobreak). Once it's gone, he's squishy and killable.",
        "Don't stand on his W (Parallel Convergence) field. If you see the circle, walk out immediately.",
        "He can't match your sustained damage. Extended fights favor you once his burst rotation is down.",
    ],
    ("Viego", "Diana"): [
        "She bursts hard with Q-E-R combo. Dodge her Q (Crescent Strike) arc — without it she can't reset E.",
        "Your W stun interrupts her engage. Time it when she E (Lunar Rush) dashes in.",
        "Build Maw of Malmortius if she's fed. The shield saves you from her burst.",
    ],
    ("Viego", "Briar"): [
        "She's extremely strong in 1v1s when her W (Blood Frenzy) is active. Kite back and wait it out.",
        "Her R is a long-range engage. Ward deep to see it coming and sidestep.",
        "Build anti-heal — her entire kit revolves around lifesteal. Executioner's Calling first back.",
    ],
    ("Viego", "Bel'Veth"): [
        "Contest her early. She's weak before she gets Void Coral (form from epic monster).",
        "If she gets her empowered form from Rift Herald or Dragon, she spikes massively. Contest objectives.",
        "She outscales you as a hypercarry. End games early or deny her resets in teamfights.",
    ],
    ("Viego", "Lillia"): [
        "She kites you hard with passive move speed from Dream-Laden Bough. W stun is mandatory to engage.",
        "She's squishy. If you land W, full combo her before she can run away.",
        "Her R (Lilting Lullaby) sleeps your team. Spread out and don't let her hit multi-person Q-R.",
    ],
    ("Viego", "Shaco"): [
        "Buy Control Wards to reveal his Q stealth. Pink ward your jungle entrances against invades.",
        "Don't chase him through boxes (W Jack in the Box). Walk around them or clear them first.",
        "You outscale heavily. He's an early-game cheese champion — survive to 2 items and you auto-win.",
    ],
    ("Viego", "Nocturne"): [
        "His spell shield (W Shroud of Darkness) blocks your W stun. Bait it with Q first, then W.",
        "He wins 1v1 early with lethal tempo and his passive sustain. Don't contest crab without backup.",
        "His R (Paranoia) denies vision. Ping your team when he hits 6 so they play safe.",
    ],
    ("Viego", "Rengar"): [
        "Ward bushes near objectives. He jumps from bushes with passive — vision denies his engage.",
        "He's stronger in 1v1 inside bushes. Fight him in open areas where he can't leap.",
        "After 1 item you match him in dueling. Don't fight him early in the river near bushes.",
    ],
    ("Viego", "Xin Zhao"): [
        "He wins 1v1 levels 2-5 hard. His Q three-hit knockup + W sustain are very strong early.",
        "Don't fight him until Kraken Slayer. After 1 item you can trade evenly.",
        "His R (Crescent Guard) knocks back everyone outside the circle. Fight inside it or wait until it ends.",
    ],
    ("Viego", "Udyr"): [
        "He runs you down with bear stance (E) stun. Don't trade autos — he wins stat-check fights early.",
        "Kite him with W stun. His weakness is being kited; he has no gap closer besides raw speed.",
        "You outscale with items. Farm safely and duel him after Kraken + Collector.",
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
    """Get tips for a specific champion vs champion matchup."""
    return MATCHUP_TIPS.get((your_champ, enemy_champ), [])


def get_role_tips(role: str) -> list[str]:
    """Get general tips for a role."""
    return ROLE_TIPS.get(role, [])


def get_all_matchup_tips(my_champ: str, enemy_champs: list[str]) -> list[dict]:
    """Get matchup tips for all enemy champions."""
    results = []
    for enemy in enemy_champs:
        tips = get_matchup_tips(my_champ, enemy)
        if tips:
            results.append({"enemy": enemy, "tips": tips})
    return results
