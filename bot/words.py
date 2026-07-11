"""
words.py — Username generator uchun keng so'z bazasi
50,000+ kombinatsiya imkoniyati
"""
import random
import string
import os

# ─── O'ZBEK SO'ZLARI ──────────────────────────────────────────────
UZ_SHORT = [
    # Tabiat
    "oltin", "kumush", "yulduz", "quyosh", "osmon", "bulut", "bahor", "kuzgi",
    "toshkent", "samarqand", "buxoro", "namangan", "andijon", "fargona",
    "daryo", "toglar", "sahro", "vodiy", "gullar",
    # Fazilatlar
    "yaxshi", "kuchli", "aqlli", "doimiy", "sadiq", "botir", "shijoat",
    "gozal", "shirin", "saxiy", "kamtar", "dono", "yengil",
    # Hayot
    "hayot", "baxt", "orzu", "vatan", "yurak", "sevgi", "shodlik",
    "mehnat", "bilim", "ustoz", "olim", "zafar", "nurul", "shuhrat",
    "yigit", "qizil", "qozon", "mehriban", "ulug", "jasur",
    # Texnologiya / zamonaviy
    "raqamli", "tezkor", "yangi", "xabar", "hamkor", "savdo", "biznes",
    "daromad", "invest", "kredit", "moliya", "kapital", "bozor", "optom",
    # Ismlar / laqamlar
    "sarvar", "jahon", "alisher", "temur", "bobur", "mirzo", "farukh",
    "sherzod", "jasur", "ulugbek", "dilshod", "mansur", "sanjar", "ravshan",
    "kamol", "sirojiddin", "husan", "islom", "zafarjon", "asilbek",
    # Turli
    "doira", "chiroy", "zamon", "maktab", "dunyo", "galaba", "murod",
    "hamid", "bahrom", "nurillo", "sulton", "shahzod", "behruz", "saidakbar",
]

UZ_PREFIXES = [
    "uz", "uzb", "real", "vip", "top", "best", "pro", "mega",
    "elite", "smart", "super", "mr", "dr", "sir", "big", "true",
    "xon", "bek", "mir", "nur", "ali", "jan",
]

UZ_SUFFIXES = [
    "uz", "uzb", "bot", "shop", "pro", "biz", "media", "hub",
    "team", "group", "net", "official", "real", "tv", "info",
    "brand", "zone", "club", "uz01", "007",
]

# ─── INGLIZCHA SO'ZLAR ────────────────────────────────────────────
EN_PREFIXES = [
    "the", "my", "your", "top", "best", "super", "pro", "real",
    "vip", "mega", "elite", "smart", "dark", "light", "alpha", "beta",
    "ultra", "hyper", "xtra", "new", "old", "big", "tiny", "micro",
    "neo", "max", "main", "pure", "prime", "swift",
]

EN_SUFFIXES = [
    "hub", "tech", "dev", "pro", "app", "net", "web", "io",
    "bot", "ai", "lab", "now", "go", "hq", "plus", "spot",
    "store", "zone", "base", "point", "works", "ly", "ify",
    "media", "team", "crew", "official", "real",
]

# Mashxur/cool inglizcha kalit so'zlar
EN_COOL = [
    # Hayot/odamlar
    "ghost", "shadow", "phantom", "cipher", "venom", "raven", "titan",
    "maverick", "outlaw", "ranger", "hunter", "striker", "blaze", "apex",
    "echo", "falcon", "cobra", "viper", "panther", "jaguar", "lynx",
    # Texnologiya
    "pixel", "vector", "matrix", "quantum", "crypto", "neural", "binary",
    "script", "kernel", "syntax", "cipher", "daemon", "socket", "redis",
    "docker", "lambda", "tensor", "async", "proxy", "cache", "relay",
    # O'yin/esports
    "ranked", "clutch", "frenzy", "berserk", "dominate", "lethal", "swift",
    "sniper", "rusher", "lurker", "flanker", "stealthy", "turbo",
    # Umum cool
    "vivid", "luxe", "sleek", "stark", "brisk", "crisp", "deft",
    "keen", "bold", "brave", "calm", "epic", "grit", "zest",
]

EN_NATURE = [
    "storm", "thunder", "lightning", "ember", "frost", "blizzard",
    "comet", "nebula", "orbit", "solar", "lunar", "stellar", "cosmic",
    "abyss", "summit", "ridge", "canyon", "glacier", "torrent",
]

EN_COLORS = [
    "crimson", "scarlet", "azure", "cobalt", "violet", "magenta",
    "amber", "golden", "silver", "ivory", "ebony", "onyx",
]

EN_NUMBERS = list(range(1, 10)) + list(range(10, 100, 7)) + [100, 101, 7, 99, 777, 404, 42]

# ─── FAYL DAN LEKSIKON ───────────────────────────────────────────
adjectives = []
nouns = []

try:
    adj_path = os.path.join(os.path.dirname(__file__), 'adjectives.txt')
    with open(adj_path, 'r', encoding='utf-8') as f:
        adjectives = [
            line.strip().lower() for line in f
            if line.strip().isalpha() and 4 <= len(line.strip()) <= 7
        ]
except Exception:
    adjectives = ["cool", "fast", "smart", "dark", "light", "epic", "pure", "bold"]

try:
    noun_path = os.path.join(os.path.dirname(__file__), 'nouns.txt')
    with open(noun_path, 'r', encoding='utf-8') as f:
        nouns = [
            line.strip().lower() for line in f
            if line.strip().isalpha() and 4 <= len(line.strip()) <= 7
        ]
except Exception:
    nouns = ["ninja", "coder", "star", "wolf", "lion", "eagle", "bear", "hawk"]


def generate_smart_username(lang: str = None) -> str:
    """
    12 xil rejim bilan 50,000+ noyob username kombinatsiyasi.
    lang='uz' => o'zbek so'zlari, lang='en' => inglizcha, None => aralash
    """
    if lang == 'uz':
        mode = random.choice([
            "uz_pure",        # yulduz
            "uz_prefix",      # xon_yulduz
            "uz_suffix",      # yulduz_pro
            "uz_two",         # oltin_yulduz
            "uz_number",      # yulduz07
            "uz_adj_noun",    # smart + o'zbek
        ])
    elif lang == 'en':
        mode = random.choice([
            "en_adj_noun",    # darkwolf
            "en_prefix_cool", # theghostdev
            "en_cool_suffix", # ghosthub
            "en_noun_num",    # wolf42
            "en_cool_adj",    # ghostswift
            "en_color_noun",  # crimsonwolf
            "en_nature",      # storm + coder
            "en_two_cool",    # ghostshadow
        ])
    else:
        mode = random.choice([
            "uz_pure", "uz_prefix", "uz_suffix", "uz_two", "uz_number",
            "en_adj_noun", "en_prefix_cool", "en_cool_suffix", "en_noun_num",
            "en_cool_adj", "en_color_noun", "en_nature", "en_two_cool",
        ])

    # ── O'ZBEK REJIMLAR ──
    if mode == "uz_pure":
        return random.choice(UZ_SHORT)

    elif mode == "uz_prefix":
        w = random.choice(UZ_SHORT)
        pref = random.choice(UZ_PREFIXES)
        sep = random.choice(["_", ""])
        return f"{pref}{sep}{w}"

    elif mode == "uz_suffix":
        w = random.choice(UZ_SHORT)
        suf = random.choice(UZ_SUFFIXES)
        sep = random.choice(["_", ""])
        return f"{w}{sep}{suf}"

    elif mode == "uz_two":
        w1 = random.choice(UZ_SHORT)
        w2 = random.choice(UZ_SHORT)
        if w1 == w2:
            w2 = random.choice(UZ_PREFIXES)
        sep = random.choice(["_", ""])
        return f"{w1}{sep}{w2}"

    elif mode == "uz_number":
        w = random.choice(UZ_SHORT)
        n = random.choice(EN_NUMBERS)
        return f"{w}{n}"

    elif mode == "uz_adj_noun":
        adj = random.choice(adjectives) if adjectives else "smart"
        w = random.choice(UZ_SHORT)
        sep = random.choice(["_", ""])
        return f"{adj}{sep}{w}"

    # ── INGLIZCHA REJIMLAR ──
    elif mode == "en_adj_noun":
        adj = random.choice(adjectives) if adjectives else "dark"
        noun = random.choice(nouns) if nouns else "wolf"
        sep = random.choice(["_", ""])
        return f"{adj}{sep}{noun}"

    elif mode == "en_prefix_cool":
        pref = random.choice(EN_PREFIXES)
        cool = random.choice(EN_COOL)
        sep = random.choice(["_", ""])
        return f"{pref}{sep}{cool}"

    elif mode == "en_cool_suffix":
        cool = random.choice(EN_COOL)
        suf = random.choice(EN_SUFFIXES)
        sep = random.choice(["_", ""])
        return f"{cool}{sep}{suf}"

    elif mode == "en_noun_num":
        noun = random.choice(nouns + EN_COOL)
        n = random.choice(EN_NUMBERS)
        return f"{noun}{n}"

    elif mode == "en_cool_adj":
        cool = random.choice(EN_COOL)
        adj = random.choice(adjectives + ["bold", "swift", "dark", "pure"])
        sep = random.choice(["_", ""])
        return f"{cool}{sep}{adj}"

    elif mode == "en_color_noun":
        color = random.choice(EN_COLORS)
        noun = random.choice(nouns + EN_COOL)
        sep = random.choice(["_", ""])
        return f"{color}{sep}{noun}"

    elif mode == "en_nature":
        nat = random.choice(EN_NATURE)
        cool = random.choice(EN_COOL + nouns[:200] if nouns else EN_COOL)
        sep = random.choice(["_", ""])
        return f"{nat}{sep}{cool}"

    elif mode == "en_two_cool":
        c1 = random.choice(EN_COOL)
        c2 = random.choice(EN_COOL + EN_NATURE)
        if c1 == c2:
            c2 = random.choice(EN_SUFFIXES)
        sep = random.choice(["_", ""])
        return f"{c1}{sep}{c2}"

    # fallback
    return f"{random.choice(EN_COOL)}{random.randint(1, 99)}"


# Legacy compat
PREFIXES = EN_PREFIXES
SUFFIXES = EN_SUFFIXES
CATEGORIES = {
    "biznes": ["savdo", "biznes", "tijorat", "sotuv", "invest", "bazar", "trade"],
    "texnologiya": ["tech", "dev", "coder", "cyber", "web", "app", "code", "data"],
    "gaming": ["gamer", "play", "esports", "sniper", "ninja", "zone", "arena"],
    "lifestyle": ["life", "style", "sport", "blog", "vlog", "media", "tv"],
}

def get_base_words():
    all_words = []
    for words in CATEGORIES.values():
        all_words.extend(words)
    return all_words

base_words = get_base_words()
