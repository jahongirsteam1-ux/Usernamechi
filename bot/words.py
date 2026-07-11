"""
words.py — Keng qamrovli username so'z bazasi
Kategoriyalar: ismlar, familiyalar, hayvonlar, o'simliklar, joylar,
               umumiy so'zlar, kasb/soha, brend/texnologiya
Mezonlar: 5-8 harf, bitta so'z, oson talaffuz, ma'noli
"""
import random
import os

# ─── TALAFFUZ FILTRI ─────────────────────────────────────────────
def _is_pronounceable(word: str) -> bool:
    vowels = set('aeiou')
    cons_run = vowel_run = 0
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
            cons_run = vowel_run = 0
    return True


# ══════════════════════════════════════════════════════════════════
#  O'ZBEK ISMLAR (erkak)
# ══════════════════════════════════════════════════════════════════
UZ_MALE_NAMES = [
    # Klassik
    "alisher", "temur", "bobur", "mirzo", "ulugbek", "jahongir",
    "sardor", "sarvar", "sherzod", "jasur", "ravshan", "dilshod",
    "mansur", "sanjar", "kamol", "islom", "shahzod", "behruz",
    "bahrom", "nurillo", "sulton", "hamid", "asilbek", "murod",
    "farukh", "husan", "zafar", "mukhlis", "ibrohim", "yusuf",
    "davron", "eldor", "eldorbek", "nodir", "nozim", "otabek",
    "akbar", "anvar", "asror", "aziz", "bekzod", "doniyor",
    "elmurod", "farrukh", "jamshid", "laziz", "lochin", "muzaffar",
    "nurbek", "obid", "olimjon", "ortiq", "oybek", "ozod",
    "parviz", "pulat", "qodir", "qodirbek", "rustam", "saidakbar",
    "sarvarbek", "sirojiddin", "tohir", "ulmas", "umid", "vohid",
    "xasan", "xusan", "xurshid", "yorqin", "zubaydullo",
    # Qisqaroq
    "ali", "azam", "baxt", "botir", "doston", "ilhom",
    "kamal", "lochin", "mumin", "nafos", "orif", "rohat",
    "samir", "shams", "shokir", "sobir", "sunnat", "tahsin",
    "vahid", "vosit", "xasan", "xorun", "zafar",
]

# ══════════════════════════════════════════════════════════════════
#  O'ZBEK ISMLAR (ayol)
# ══════════════════════════════════════════════════════════════════
UZ_FEMALE_NAMES = [
    "malika", "nilufar", "zulfiya", "dildora", "kamola", "mohira",
    "nasiba", "nodira", "oydin", "oysha", "parizod", "sarvinoz",
    "shahlo", "shaxlo", "sitora", "umida", "xurmo", "yulduz",
    "zilola", "zuhra", "aziza", "barno", "dilorom", "feruza",
    "gavhar", "gulnora", "hulkar", "iroda", "kumush", "lola",
    "lobar", "maftuna", "mahliyo", "manzura", "mavluda", "muazzam",
    "munira", "mushtariy", "nafisa", "nargiza", "nozima", "noziya",
    "oygul", "ozoda", "ra'no", "rohila", "sabohat", "sadoqat",
    "sanam", "sarvar", "saodat", "sevara", "shahnoza", "shirin",
    "soliha", "surayyo", "tabassum", "tursunoy", "ulmas", "xilola",
]

# ══════════════════════════════════════════════════════════════════
#  O'ZBEK FAMILIYALAR (5-8 harf)
# ══════════════════════════════════════════════════════════════════
UZ_SURNAMES = [
    "karimov", "rahimov", "hasanov", "umarov", "nazarov",
    "yusupov", "mirzaev", "toshmatov", "xolmatov", "ergashev",
    "nishonov", "ismoilov", "salimov", "qodirov", "abdullayev",
    "normatov", "tojimatov", "xasanov", "yunusov", "valiyev",
    "botirov", "razzaqov", "tursunov", "holiqov", "sobirov",
    "zokirov", "haydarov", "choriyev", "murodov", "eshmatov",
]

# ══════════════════════════════════════════════════════════════════
#  INGLIZ ISMLAR (5-8 harf, mashhur)
# ══════════════════════════════════════════════════════════════════
EN_MALE_NAMES = [
    # Klassik
    "james", "oliver", "lucas", "ethan", "mason", "logan",
    "jacob", "liam", "noah", "aiden", "caleb", "dylan",
    "henry", "samuel", "jackson", "carter", "hunter", "jordan",
    "connor", "xavier", "landon", "austin", "blake", "chase",
    "derek", "evan", "felix", "grant", "hayes", "ivan",
    "jason", "keegan", "lance", "miles", "nolan", "oscar",
    "parker", "quinn", "ryder", "seth", "tyler", "victor",
    "wade", "wyatt",
    # Cool laqamlar
    "axel", "blade", "colt", "dash", "fox", "rex",
    "zane", "ace", "brock", "cole", "drew", "finn",
    "grey", "jace", "kai", "knox", "lane", "nash",
    "reid", "rhys", "ross", "ryan", "sean", "troy",
]

EN_FEMALE_NAMES = [
    "emma", "olivia", "ava", "mia", "luna", "aria",
    "sofia", "chloe", "isla", "aurora", "riley", "nora",
    "lily", "ellie", "nova", "grace", "hazel", "ivy",
    "layla", "zoe", "stella", "maya", "leah", "ruby",
    "alice", "amber", "bella", "claire", "diana", "eden",
    "faith", "gemma", "hanna", "irene", "julia", "karen",
    "laura", "megan", "naomi", "piper", "quinn", "robin",
    "sarah", "tessa", "vera", "willow", "xena",
]

# ══════════════════════════════════════════════════════════════════
#  HAYVONLAR — barcha turlar
# ══════════════════════════════════════════════════════════════════
ANIMALS = [
    # Yirtqichlar
    "tiger", "leopard", "jaguar", "cheetah", "puma", "cougar",
    "panther", "lynx", "ocelot", "caracal", "serval",
    "wolf", "coyote", "jackal", "hyena", "dingo",
    "bear", "grizzly", "kodiak", "panda",
    "lion", "lioness",
    # Qushlar
    "eagle", "falcon", "hawk", "osprey", "condor", "buzzard",
    "raven", "crow", "magpie", "jackdaw", "rook",
    "owl", "barn", "horned",
    "crane", "heron", "stork", "pelican", "albatross",
    "swift", "swallow", "martin", "wren", "robin",
    "parrot", "macaw", "toucan", "hornbill",
    "peacock", "pheasant", "quail", "grouse",
    "penguin", "puffin", "gannet",
    # Dengiz
    "shark", "orca", "dolphin", "narwhal", "beluga",
    "walrus", "seal", "otter", "beaver",
    "marlin", "swordfish", "barracuda",
    # Hasharotlar / boshqa
    "mantis", "hornet", "cobra", "viper", "mamba",
    "gecko", "iguana", "chameleon",
    # O'zbek hayvonlar
    "lochin", "burgut", "layli", "qoqnur", "bulbul",
    "tuya", "ilon",
    # Qo'shimcha
    "bison", "moose", "caribou", "reindeer", "elk",
    "rhino", "hippo", "giraffe", "zebra", "gazelle",
    "impala", "kudu", "oryx", "addax",
    "gorilla", "gibbon", "baboon", "mandrill",
    "badger", "ferret", "weasel", "mink", "skunk",
    "raccoon", "opossum", "armadillo",
    "mongoose", "meerkat", "suricate",
    "capybara", "nutria", "muskrat",
    "porcupine", "hedgehog", "platypus",
    "kangaroo", "wallaby", "koala", "wombat", "quokka",
    "dingo", "numbat", "quoll", "bandicoot",
]

# Faqat 5-8 harfli hayvon nomlari (filtrlash)
ANIMALS_CLEAN = [
    a for a in ANIMALS
    if a.isalpha() and 5 <= len(a) <= 8 and _is_pronounceable(a)
]

# ══════════════════════════════════════════════════════════════════
#  O'SIMLIKLAR, RANGLAR, MINERALLAR
# ══════════════════════════════════════════════════════════════════
NATURE_WORDS = [
    # O'simliklar
    "cedar", "birch", "maple", "aspen", "willow", "laurel",
    "lotus", "daisy", "lilac", "fern", "clover", "ivy",
    "cactus", "agave", "bamboo", "bonsai",
    # Minerallar / toshlar
    "onyx", "amber", "garnet", "jasper", "opal", "topaz",
    "zircon", "quartz", "agate", "obsidian", "granite",
    "cobalt", "silver", "golden", "ivory", "ebony",
    # Tabiat hodisalari
    "storm", "frost", "ember", "comet", "lunar", "solar",
    "aurora", "zenith", "nadir", "vortex",
    "ridge", "canyon", "summit", "delta", "tundra",
    "steppe", "savanna", "prairie",
    "glacier", "iceberg", "torrent", "cascade",
    "monsoon", "typhoon", "cyclone",
]
NATURE_CLEAN = [
    w for w in NATURE_WORDS
    if w.isalpha() and 5 <= len(w) <= 8 and _is_pronounceable(w)
]

# ══════════════════════════════════════════════════════════════════
#  UMUMIY INGLIZCHA SO'ZLAR (ma'noli, cool)
# ══════════════════════════════════════════════════════════════════
EN_COOL_WORDS = [
    # Xarakter
    "ghost", "shadow", "phantom", "cipher", "ranger", "hunter",
    "outlaw", "nomad", "archer", "knight", "herald", "rogue",
    "maverick", "pioneer", "voyager", "pilgrim", "wanderer",
    "sentinel", "guardian", "champion", "warrior", "wizard",
    "alchemist", "oracle", "prophet", "sage",
    # Texnologiya
    "pixel", "vector", "cipher", "kernel", "socket", "relay",
    "lambda", "tensor", "proxy", "cache", "script", "daemon",
    "beacon", "signal", "pulse", "nexus", "vertex",
    "matrix", "binary", "quantum", "crypto", "neural",
    # Sifatlar (username bo'la oladi)
    "vivid", "stark", "brisk", "crisp", "sleek", "prime",
    "swift", "blaze", "surge", "bold", "brave", "deft",
    "keen", "pure", "apex", "peak",
    # Biznes / brend
    "venture", "anchor", "bridge", "harbor", "forge", "atlas",
    "vault", "haven", "citadel", "bastion", "pinnacle",
    "summit", "zenith", "apex",
]
EN_COOL_CLEAN = [
    w for w in EN_COOL_WORDS
    if w.isalpha() and 5 <= len(w) <= 8 and _is_pronounceable(w)
]

# ══════════════════════════════════════════════════════════════════
#  O'ZBEK UMUMIY SO'ZLAR
# ══════════════════════════════════════════════════════════════════
UZ_WORDS_GENERAL = [
    # Tabiat
    "oltin", "kumush", "yulduz", "quyosh", "osmon", "bulut",
    "bahor", "daryo", "sahro", "vodiy", "shamol", "dengiz",
    # Fazilatlar
    "yaxshi", "kuchli", "aqlli", "sadiq", "botir", "gozal",
    "shirin", "saxiy", "dono", "yengil", "jasur", "ulug",
    # Hayot
    "hayot", "baxt", "orzu", "vatan", "yurak", "sevgi",
    "zafar", "shuhrat", "bilim", "mehnat", "galaba", "murod",
    # Shaharlar
    "toshkent", "buxoro", "namangan", "andijon", "fargona",
    "samarqand",
    # Boshqa
    "doira", "chiroy", "zamon", "maktab", "dunyo",
    "kapital", "bozor", "raqam",
]
UZ_WORDS_CLEAN = [
    w for w in UZ_WORDS_GENERAL
    if w.isalpha() and 5 <= len(w) <= 8
]

# ══════════════════════════════════════════════════════════════════
#  BARCHA POOL (legacy compat uchun)
# ══════════════════════════════════════════════════════════════════
UZ_WORDS = UZ_WORDS_GENERAL + [
    n for n in UZ_MALE_NAMES + UZ_FEMALE_NAMES
    if n.isalpha() and 5 <= len(n) <= 8
]
UZ_SHORT = UZ_WORDS  # backward compat

# Barcha inglizcha so'zlar to'plami
EN_ALL_POOL = list(set(
    EN_MALE_NAMES + EN_FEMALE_NAMES +
    ANIMALS_CLEAN + NATURE_CLEAN + EN_COOL_CLEAN
))
EN_WORDS_COMMON = EN_ALL_POOL
EN_COOL = EN_ALL_POOL

# ─── FAYLDAN YUKLANADIGAN SO'ZLAR ────────────────────────────────
adjectives = []
nouns = []

try:
    adj_path = os.path.join(os.path.dirname(__file__), 'adjectives.txt')
    with open(adj_path, 'r', encoding='utf-8') as f:
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


# ══════════════════════════════════════════════════════════════════
#  ASOSIY GENERATOR
# ══════════════════════════════════════════════════════════════════
def generate_quality_username(lang: str = None) -> str:
    """
    Sifatli bitta username qaytaradi.
    Barcha kategoriyalardan: ismlar, hayvonlar, so'zlar, tabiat.
    """
    if lang == 'uz':
        # O'zbek: ism, so'z, yoki lug'at
        category = random.choices(
            ["uz_name_m", "uz_name_f", "uz_word", "uz_surname", "dict_noun"],
            weights=[30, 15, 30, 10, 15], k=1
        )[0]
    elif lang == 'en':
        # Ingliz: ism, hayvon, so'z, tabiat, lug'at
        category = random.choices(
            ["en_name_m", "en_name_f", "animal", "cool", "nature", "dict_noun", "dict_adj"],
            weights=[20, 10, 25, 20, 10, 10, 5], k=1
        )[0]
    else:
        category = random.choices(
            ["uz_name_m", "uz_word", "en_name_m", "animal", "cool", "nature", "dict_noun"],
            weights=[15, 15, 15, 25, 15, 10, 5], k=1
        )[0]

    # Kategoriya bo'yicha tanlov
    if category == "uz_name_m":
        pool = [n for n in UZ_MALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
        return random.choice(pool) if pool else random.choice(UZ_WORDS_CLEAN)

    elif category == "uz_name_f":
        pool = [n for n in UZ_FEMALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
        return random.choice(pool) if pool else random.choice(UZ_WORDS_CLEAN)

    elif category == "uz_surname":
        pool = [s for s in UZ_SURNAMES if s.isalpha() and 5 <= len(s) <= 8]
        return random.choice(pool) if pool else random.choice(UZ_WORDS_CLEAN)

    elif category == "uz_word":
        return random.choice(UZ_WORDS_CLEAN) if UZ_WORDS_CLEAN else "yulduz"

    elif category == "en_name_m":
        pool = [n for n in EN_MALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
        return random.choice(pool) if pool else random.choice(EN_ALL_POOL)

    elif category == "en_name_f":
        pool = [n for n in EN_FEMALE_NAMES if n.isalpha() and 5 <= len(n) <= 8]
        return random.choice(pool) if pool else random.choice(EN_ALL_POOL)

    elif category == "animal":
        return random.choice(ANIMALS_CLEAN) if ANIMALS_CLEAN else "falcon"

    elif category == "cool":
        return random.choice(EN_COOL_CLEAN) if EN_COOL_CLEAN else "ghost"

    elif category == "nature":
        return random.choice(NATURE_CLEAN) if NATURE_CLEAN else "storm"

    elif category == "dict_noun":
        pool = [w for w in nouns if 5 <= len(w) <= 8]
        return random.choice(pool) if pool else random.choice(EN_ALL_POOL)

    elif category == "dict_adj":
        pool = [w for w in adjectives if 5 <= len(w) <= 8]
        return random.choice(pool) if pool else random.choice(EN_ALL_POOL)

    return random.choice(EN_ALL_POOL)


# Legacy alias
def generate_smart_username(lang: str = None) -> str:
    return generate_quality_username(lang=lang)


# Legacy constants
UZ_PREFIXES = []
UZ_SUFFIXES = []
EN_PREFIXES = []
EN_NUMBERS = []

CATEGORIES = {
    "biznes": ["kapital", "bozor", "savdo"],
    "texnologiya": ["cipher", "kernel", "pixel"],
    "gaming": ["ranger", "hunter", "archer"],
    "lifestyle": ["vivid", "prime", "sleek"],
}

def get_base_words():
    all_words = []
    for words in CATEGORIES.values():
        all_words.extend(words)
    return all_words

base_words = get_base_words()
