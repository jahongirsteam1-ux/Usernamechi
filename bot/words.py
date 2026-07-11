"""
words.py — Sifatli username generator
Mezonlar:
  • 5-8 harf (qimmatli diapazon)
  • Raqamsiz yoki minimal raqam
  • Bitta tushunarli so'z (ikki so'z yopishtirilmasin)
  • Oson talaffuz
  • Underscore minimallashtirilgan
  • Kamyob lekin ma'noli
"""
import random
import os

# ─── SIFAT FILTRI ────────────────────────────────────────────────
def _is_pronounceable(word: str) -> bool:
    """
    So'z uchta ketma-ket undoshsiz va uchta ketma-ket unli bo'lmasin.
    """
    vowels = set('aeiou')
    cons_run = 0
    vowel_run = 0
    for ch in word.lower():
        if ch in vowels:
            cons_run = 0
            vowel_run += 1
            if vowel_run > 3:
                return False
        elif ch.isalpha():
            vowel_run = 0
            cons_run += 1
            if cons_run > 3:
                return False
        else:
            cons_run = 0
            vowel_run = 0
    return True


# ─── O'ZBEK SO'ZLARI (5-8 harf, ma'noli, oson talaffuz) ──────────
# Faqat mustaqil so'zlar — ikki so'z yopishtirilmagan
UZ_WORDS = [
    # Tabiat / joy
    "oltin", "kumush", "yulduz", "quyosh", "osmon", "bulut", "bahor",
    "daryo", "sahro", "vodiy", "toglar", "shamol", "dengiz",
    # Fazilatlar
    "yaxshi", "kuchli", "aqlli", "sadiq", "botir", "gozal", "shirin",
    "saxiy", "kamtar", "dono", "yengil", "jasur", "ulug",
    # Hayot
    "hayot", "baxt", "orzu", "vatan", "yurak", "sevgi", "zafar",
    "shuhrat", "bilim", "mehnat", "galaba", "murod", "chiroy",
    # Ismlar (5-8 harf)
    "sarvar", "jahon", "temur", "bobur", "mirzo", "farukh",
    "sherzod", "jasur", "dilshod", "mansur", "sanjar", "ravshan",
    "kamol", "husan", "islom", "shahzod", "behruz", "bahrom",
    "nurillo", "sulton", "hamid", "asilbek", "mukhlis",
    # Zamonaviy / brend
    "tezkor", "yangi", "xabar", "hamkor", "savdo", "kapital",
    "bozor", "raqam", "zamon", "maktab", "dunyo",
    # Shahарlar (5-8 harf)
    "toshkent", "buxoro", "namangan", "andijon", "fargona",
]

# ─── INGLIZCHA SO'ZLAR (5-8 harf, lug'atda bor, oson talaffuz) ──
# Bitta real ingliz so'zi — gluing yo'q

EN_WORDS_COMMON = [
    # Hayvonlar
    "falcon", "raven", "viper", "cobra", "titan", "eagle",
    "lynx", "panda", "tiger", "rhino", "bison", "otter",
    "moose", "crane", "swift", "robin",
    # Tabiat
    "storm", "frost", "ember", "comet", "lunar", "solar",
    "ridge", "canyon", "summit", "glacier", "torrent",
    # Texnologiya / brend
    "pixel", "vector", "cipher", "kernel", "socket", "relay",
    "lambda", "tensor", "proxy", "cache", "script",
    # Xarakter / laqam
    "ghost", "shadow", "ranger", "hunter", "outlaw", "nomad",
    "archer", "knight", "herald", "rogue", "maverick",
    # Fazilatlar / sifat (yolg'iz so'z sifatida username bo'la oladi)
    "vivid", "stark", "brisk", "crisp", "deft", "bold",
    "brave", "sleek", "prime", "swift", "blaze", "surge",
    # Iqtisodiy / biznes
    "venture", "nexus", "beacon", "anchor", "bridge", "harbor",
    "signal", "source", "forge", "atlas", "vault",
    # O'yin / esports
    "clutch", "frenzy", "lethal", "turbo", "ranked",
    # Rang
    "cobalt", "amber", "silver", "ivory", "ebony", "onyx",
    "violet", "indigo", "scarlet", "crimson",
]

EN_WORDS_5 = [w for w in EN_WORDS_COMMON if len(w) == 5]
EN_WORDS_6 = [w for w in EN_WORDS_COMMON if len(w) == 6]
EN_WORDS_7 = [w for w in EN_WORDS_COMMON if len(w) == 7]
EN_WORDS_8 = [w for w in EN_WORDS_COMMON if len(w) == 8]

# ─── FAYLDAN YUKLANADIGAN SO'ZLAR ────────────────────────────────
adjectives = []
nouns = []

try:
    adj_path = os.path.join(os.path.dirname(__file__), 'adjectives.txt')
    with open(adj_path, 'r', encoding='utf-8') as f:
        # Faqat 5-8 harfli, sof harf, oson talaffuz qilinadigan
        adjectives = [
            w for w in (line.strip().lower() for line in f)
            if w.isalpha() and 5 <= len(w) <= 8 and _is_pronounceable(w)
        ]
except Exception:
    adjectives = ["vivid", "sleek", "stark", "crisp", "swift", "bold", "prime"]

try:
    noun_path = os.path.join(os.path.dirname(__file__), 'nouns.txt')
    with open(noun_path, 'r', encoding='utf-8') as f:
        nouns = [
            w for w in (line.strip().lower() for line in f)
            if w.isalpha() and 5 <= len(w) <= 8 and _is_pronounceable(w)
        ]
except Exception:
    nouns = ["ghost", "storm", "eagle", "tiger", "falcon", "raven", "cobra"]


# ─── ASOSIY GENERATOR ────────────────────────────────────────────
def generate_quality_username(lang: str = None) -> str:
    """
    Mezonlarga mos bitta sifatli username:
    - 5-8 harf
    - Bitta so'z (yoki juda tabiiy juftlik)
    - Raqam yo'q (asosiy holat)
    - Underscore yo'q (asosiy holat)
    - Oson talaffuz
    """
    if lang == 'uz':
        strategy = random.choices(
            ["uz_pure", "uz_pure", "uz_lug'at"],
            weights=[60, 30, 10], k=1
        )[0]
    elif lang == 'en':
        strategy = random.choices(
            ["en_curated", "en_curated", "en_dict", "en_dict_adj"],
            weights=[40, 30, 20, 10], k=1
        )[0]
    else:
        strategy = random.choices(
            ["uz_pure", "en_curated", "en_dict", "en_dict_adj", "uz_lug'at"],
            weights=[25, 30, 25, 15, 5], k=1
        )[0]

    if strategy == "uz_pure":
        # Toza o'zbek so'zi, 5-8 harf
        pool = [w for w in UZ_WORDS if 5 <= len(w) <= 8]
        return random.choice(pool) if pool else random.choice(UZ_WORDS)

    elif strategy == "uz_lug'at":
        # nouns/adjectives lug'atidan o'zbek-yaqin so'z (aslida ingliz lug'at)
        pool = [w for w in nouns if 5 <= len(w) <= 7]
        return random.choice(pool) if pool else random.choice(UZ_WORDS)

    elif strategy == "en_curated":
        # Eng sifatli insoniy tanlangan ingliz so'zlari
        pool = EN_WORDS_5 + EN_WORDS_6 + EN_WORDS_7
        # 6 harflilar biroz ustunroq (optimal uzunlik)
        weighted = EN_WORDS_6 * 3 + EN_WORDS_5 * 2 + EN_WORDS_7 * 2 + EN_WORDS_8
        return random.choice(weighted) if weighted else random.choice(EN_WORDS_COMMON)

    elif strategy == "en_dict":
        # Lug'atdan sifatli noun
        pool = [w for w in nouns if 5 <= len(w) <= 7]
        return random.choice(pool) if pool else random.choice(EN_WORDS_COMMON)

    elif strategy == "en_dict_adj":
        # Lug'atdan sifatli adjective
        pool = [w for w in adjectives if 5 <= len(w) <= 7]
        return random.choice(pool) if pool else random.choice(EN_WORDS_COMMON)

    return random.choice(EN_WORDS_COMMON)


# ─── GENERATE USERNAMES (asosiy funksiya) ─────────────────────────
def generate_smart_username(lang: str = None) -> str:
    """generate_quality_username uchun alias (legacy)"""
    return generate_quality_username(lang=lang)


# ─── LEGACY COMPAT ───────────────────────────────────────────────
UZ_SHORT = UZ_WORDS  # backward compat
UZ_PREFIXES = []     # endi ishlatilmaydi
UZ_SUFFIXES = []
EN_PREFIXES = []
EN_COOL = EN_WORDS_COMMON
EN_NUMBERS = []

CATEGORIES = {
    "biznes": ["savdo", "biznes", "kapital", "invest", "bozor"],
    "texnologiya": ["cipher", "kernel", "vector", "socket", "pixel"],
    "gaming": ["clutch", "ranked", "frenzy", "lethal", "turbo"],
    "lifestyle": ["vivid", "prime", "sleek", "surge", "blaze"],
}

def get_base_words():
    all_words = []
    for words in CATEGORIES.values():
        all_words.extend(words)
    return all_words

base_words = get_base_words()
