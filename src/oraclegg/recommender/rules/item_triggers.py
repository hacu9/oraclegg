"""Item trigger rules for the tip engine.

Maps specific enemy item purchases to actionable advice.
"""

# (item_id, item_name, tip_message, priority)
# Priority: 0=urgent, 1=important, 2=info
ITEM_TRIGGERS = [
    # Crit / ADC spikes
    (3031, "Infinity Edge", "massive crit spike — avoid extended trades, burst or disengage", 1),
    (6672, "Kraken Slayer", "strong DPS — don't let them auto freely, short trades", 1),
    (3094, "Rapid Firecannon", "extended auto range — watch for poke autos", 2),
    (3085, "Runaan's Hurricane", "AoE autos in teamfights — don't stack on top of each other", 2),
    (3046, "Phantom Dancer", "attack speed + ghosting — harder to kite", 2),

    # Lethality / Assassin
    (6676, "The Collector", "execute passive — don't fight low HP", 1),
    (6694, "Serylda's Grudge", "armor pen + slow — kiting is harder", 1),
    (6697, "Hubris", "gets AD on kills — shut them down early or they snowball", 2),
    (6698, "Voltaic Cyclosword", "slow on dash — they'll stick to you after gap closing", 2),

    # AP burst
    (3089, "Rabadon's Deathcap", "huge AP spike — respect burst damage", 0),
    (4645, "Shadowflame", "strong AP burst — respect one-shot potential", 1),
    (4646, "Stormsurge", "burst + MS on kill — don't clump in teamfights", 1),
    (6655, "Luden's Echo", "poke + burst damage up significantly", 1),
    (3118, "Malignance", "ult cooldown reduced — they'll have ult more often", 2),
    (3152, "Hextech Rocketbelt", "has a dash + burst — watch for gap close", 1),

    # Defensive / Sustain
    (6333, "Death's Dance", "harder to burst — need to CC chain or focus others", 1),
    (3065, "Spirit Visage", "increased healing — consider anti-heal if you haven't", 1),
    (6673, "Immortal Shieldbow", "lifeline shield when low — burst through or back off", 1),
    (3026, "Guardian Angel", "has revive — bait GA first or focus someone else", 1),
    (3157, "Zhonya's Hourglass", "can go invulnerable — bait stasis before committing cooldowns", 1),
    (3053, "Sterak's Gage", "shield when low + tenacity — harder to burst and CC", 1),
    (3156, "Maw of Malmortius", "magic damage shield — don't waste AP burst when shield is up", 1),
    (6610, "Sundered Sky", "heals on first hit to champs — avoid short trades", 1),

    # Tank
    (3143, "Randuin's Omen", "reduces your crit damage — crit is less effective", 2),
    (3110, "Frozen Heart", "reduces attack speed near them — bad to auto near this target", 2),
    (3075, "Thornmail", "reflects damage + Grievous Wounds on autos — don't auto them if you rely on healing", 1),
    (3742, "Dead Man's Plate", "MS boost + empowered auto — they can roam fast and engage", 2),

    # Anti-heal
    (3033, "Mortal Reminder", "enemy has Grievous Wounds — your healing is reduced in fights", 1),
    (3165, "Morellonomicon", "enemy has Grievous Wounds — your healing is reduced in fights", 1),

    # Penetration
    (3036, "Lord Dominik's Regards", "armor pen — tanks take more damage", 1),
    (3135, "Void Staff", "35% magic pen — MR is much less effective now", 1),

    # Utility / Engage
    (6631, "Stridebreaker", "has a slow active — harder to kite this target", 1),
    (3078, "Trinity Force", "strong dueling — avoid 1v1 unless you're ahead", 1),
    (6692, "Eclipse", "shield + armor pen on proc — short trades hurt, go all-in or don't trade", 1),

    # Support
    (3222, "Mikael's Blessing", "can cleanse CC from allies — don't rely on a single CC to lock down their carry", 2),
    (3190, "Locket of the Iron Solari", "team shield active — burst windows need to be bigger", 2),
]

# Build as a dict for fast lookup
ITEM_TRIGGER_MAP = {item_id: (name, msg, prio) for item_id, name, msg, prio in ITEM_TRIGGERS}
