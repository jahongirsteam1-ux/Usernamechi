"""
uz_words_gen.py
Kengaytirilgan O'zbekcha so'zlar generatori.
O'zak so'zlarga qo'shimchalar qo'shish orqali 10,000+ ma'noli username yasaydi.
"""

UZ_ROOTS = [
    # IT / Texnologiya
    "dastur", "kod", "tizim", "tarmoq", "ilov", "sayt", "komp", 
    "texno", "kripto", "haker", "koder", "robot", "suniy", "bilim",
    
    # Biznes / Savdo
    "dokon", "savdo", "biznes", "bozor", "sotuv", "xarid", "pul", 
    "daromad", "foyda", "invest", "kredit", "boylik", "moliy", "tanga",
    "kassa", "hisob",
    
    # Vaqt / Holat
    "bugun", "erta", "hozir", "kecha", "zamon", "davr", "vaqt", "kun",
    "tun", "oy", "yil", "bahor", "yoz", "kuz", "qish", "tong", "oqshom",
    
    # Kasb / Mutaxassislik
    "muallim", "ustoz", "talaba", "shifokor", "doktor", "haydovchi",
    "sotuvchi", "ishchi", "usta", "rahbar", "boshliq", "lider", "admin",
    
    # Sifat / Xususiyat
    "sev", "sevimli", "yaxshi", "yangi", "eski", "gozal", "shirin", 
    "kuch", "aqlli", "dono", "tez", "zor", "ajoyib", "qiziq", "baxt",
    "omad", "quvonch", "kulg", "mehr", "orzu", "umid", "niyat", "tilak",
    "halol", "toza", "pok", "sodiq", "botir", "jasur",
    
    # Hayot / Jamiyat
    "hayot", "vatan", "xalq", "inson", "odam", "dunyo", "olam", "shahar",
    "qishloq", "mahalla", "kocha", "uy", "oila", "ota", "ona", "aka", "uka",
    "opa", "singil", "farzand", "bola", "qiz", "yigit", "dost", "ogha",
    
    # Tabiat / Narsalar
    "osmon", "quyosh", "oy", "yulduz", "bulut", "yomgir", "qor", "shamol",
    "tog", "tosh", "daryo", "dengiz", "suv", "gul", "daraxt", "meva",
    "olma", "anor", "uzum", "qovun", "tarvuz", "non", "osh", "choy",
    "kitob", "daftar", "qalam", "maktab", "dars", "ilm", "fan", "sport",
    "oyin", "kino", "musiqa", "qoshiq", "sanat",
    
    # Ranglar
    "oq", "qora", "qizil", "sariq", "yashil", "kok", "moviy", "pushti",
    
    # Ismlarga xos
    "temur", "bobur", "alisher", "amir", "mirzo", "sulton", "shoh", 
    "bek", "xon", "jon", "oy", "gul",
]

UZ_SUFFIXES = [
    "", "chi", "lash", "lar", "ga", "gi", "li", "siz", "kor", "dor", 
    "xon", "jon", "bek", "im", "miz", "ing", "shoh", "oy", "voy", "boy",
    "uz", "uzb", "pro", "bot", "vip", "zo", "zor", "lider", "best"
]

def generate_uzbek_variations() -> list:
    """O'zaklarga qo'shimchalar qo'shib ro'yxat qaytaradi."""
    words = set()
    for root in UZ_ROOTS:
        for suffix in UZ_SUFFIXES:
            word = root + suffix
            if len(word) >= 5 and word.isalpha():
                words.add(word)
    return list(words)

# Dinamik generatsiya
UZ_DYNAMIC_WORDS = generate_uzbek_variations()
