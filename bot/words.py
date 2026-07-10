import random
import string
import os

# Original Uzbek and specific keywords
PREFIXES = ["the", "my", "top", "best", "super", "pro", "uz", "uzb", "real", "vip", "mega", "ideal", "smart", "elite", "mr", "dr", "sir"]
SUFFIXES = ["bot", "uz", "uzb", "shop", "store", "market", "biz", "pro", "tech", "dev", "app", "hub", "net", "group", "team", "inc", "co", "llc", "corp"]

CATEGORIES = {
    "biznes": ["savdo", "biznes", "tijorat", "sotuv", "moliya", "invest", "daromad", "foyda", "bazar", "bozor", "trade", "deal", "optom", "retail"],
    "texnologiya": ["tech", "dev", "coder", "hacker", "it", "cyber", "web", "app", "soft", "code", "data", "cloud", "ai", "system"],
    "gaming": ["gamer", "play", "game", "esports", "sniper", "ninja", "pro", "noob", "win", "gg", "zone", "arena"],
    "lifestyle": ["life", "style", "auto", "sport", "news", "info", "media", "blog", "vlog", "channel", "tv"]
}

def get_base_words():
    all_words = []
    for words in CATEGORIES.values():
        all_words.extend(words)
    return all_words

base_words = get_base_words()

# Load large English dictionaries if available
adjectives = []
nouns = []

try:
    adj_path = os.path.join(os.path.dirname(__file__), 'adjectives.txt')
    with open(adj_path, 'r', encoding='utf-8') as f:
        # filter to words that are 3-8 chars long and purely alphabetical
        adjectives = [line.strip().lower() for line in f if line.strip().isalpha() and 3 <= len(line.strip()) <= 8]
except Exception:
    adjectives = ["cool", "fast", "smart", "dark", "light", "super", "epic", "good", "nice", "pure"]

try:
    noun_path = os.path.join(os.path.dirname(__file__), 'nouns.txt')
    with open(noun_path, 'r', encoding='utf-8') as f:
        # filter to words that are 3-8 chars long and purely alphabetical
        nouns = [line.strip().lower() for line in f if line.strip().isalpha() and 3 <= len(line.strip()) <= 8]
except Exception:
    nouns = ["ninja", "coder", "star", "hero", "king", "queen", "wolf", "dragon", "bear", "lion"]

def generate_smart_username():
    """Juda keng ma'lumotlar bazasidan foydalanib username yaratish"""
    
    # Randomly decide which type of username to generate
    mode = random.choice(["uzbek_base", "english_adj_noun", "english_noun_number", "uzbek_hybrid"])
    
    if mode == "uzbek_base":
        w1 = random.choice(base_words)
        w2 = random.choice(base_words)
        pref = random.choice(PREFIXES)
        suff = random.choice(SUFFIXES)
        formats = [
            f"{pref}_{w1}",
            f"{w1}_{suff}",
            f"{w1}{w2}",
            f"{w1}{random.randint(10, 999)}",
            f"{w1}_{random.choice(string.ascii_lowercase)}{random.randint(1, 9)}"
        ]
        return random.choice(formats)
        
    elif mode == "english_adj_noun":
        adj = random.choice(adjectives)
        noun = random.choice(nouns)
        formats = [
            f"{adj}{noun}",
            f"{adj}_{noun}",
            f"the{adj}{noun}",
            f"{adj}{noun}{random.randint(1, 99)}"
        ]
        return random.choice(formats)
        
    elif mode == "english_noun_number":
        noun = random.choice(nouns)
        formats = [
            f"{noun}{random.randint(100, 9999)}",
            f"{noun}_{random.randint(10, 99)}",
            f"real_{noun}",
            f"{noun}official"
        ]
        return random.choice(formats)
        
    else: # uzbek_hybrid
        adj = random.choice(adjectives)
        ubase = random.choice(base_words)
        formats = [
            f"{adj}_{ubase}",
            f"{adj}{ubase}",
            f"{ubase}_{adj}"
        ]
        return random.choice(formats)
