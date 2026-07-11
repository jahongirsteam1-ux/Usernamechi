"""
================================================
 main.py — Username Sniper SaaS Bot
================================================
 Barcha modullar bitta faylga birlashtirildi
 (Railway deployment uchun optimallashtirilgan)
================================================
"""
import asyncio
import logging
import os
import re
import random
import string
import hashlib
import hmac
import json
import time
import aiosqlite

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    WebAppInfo, ReplyKeyboardRemove
)
from aiogram.filters import CommandStart, Command
from dotenv import load_dotenv

from fastapi import FastAPI, Request, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

load_dotenv()

# ─── SOZLAMALAR ──────────────────────────────
BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
ADMIN_CHANNEL = int(os.getenv("ADMIN_CHANNEL", "0"))
API_ID        = int(os.getenv("API_ID", "0"))
API_HASH      = os.getenv("API_HASH", "")
ADMIN_IDS     = [int(x) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip()]
DB_PATH       = os.getenv("DB_PATH", "saas.db")
WEB_URL       = os.getenv("WEB_HOST", "https://your-app.railway.app")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

# ─── MA'LUMOTLAR BAZASI ───────────────────────
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                balance INTEGER DEFAULT 0,
                session_string TEXT,
                free_searches INTEGER DEFAULT 1
            )
        """)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN free_searches INTEGER DEFAULT 1")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                category TEXT,
                quantity INTEGER,
                price INTEGER,
                status TEXT DEFAULT 'pending',
                registered_count INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS registered_usernames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                username TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                photo_id TEXT,
                amount INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                expected_amount INTEGER,
                status TEXT DEFAULT 'pending',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                category TEXT,
                paid_qty INTEGER DEFAULT 1,
                status TEXT DEFAULT 'searching',
                created_at REAL DEFAULT (strftime('%s','now')),
                lang TEXT DEFAULT 'uz'
            )
        """)
        try:
            await db.execute("ALTER TABLE search_tasks ADD COLUMN lang TEXT DEFAULT 'uz'")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_id INTEGER,
                username TEXT,
                status TEXT DEFAULT 'free',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                username TEXT,
                status TEXT DEFAULT 'monitoring',
                created_at REAL DEFAULT (strftime('%s','now'))
            )
        """)
        await db.commit()
        # Sozlamalarni kiritish
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_card', '8600123456789012')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_channel_id', '0')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('username_price', '5000')")
        await db.commit()

        # Migration: mavjud jadvallarni yangi ustunlar bilan yangilash
        try:
            await db.execute("ALTER TABLE search_tasks ADD COLUMN paid_qty INTEGER DEFAULT 1")
            await db.commit()
        except Exception:
            pass  # Ustun allaqachon mavjud
    logger.info("✅ Baza tayyor")

async def get_setting(key, default=None):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else default

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?", (key, str(value), str(value)))
        await db.commit()

async def get_user(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)) as cur:
            row = await cur.fetchone()
            if row and 'free_searches' not in row.keys():
                return dict(row, free_searches=1)
            return dict(row) if row else None

async def create_user(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (telegram_id, balance) VALUES (?, 5000)", (telegram_id,))
        await db.commit()

async def update_balance(telegram_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (amount, telegram_id))
        await db.commit()

async def deduct_balance(telegram_id, amount):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=balance-? WHERE telegram_id=?", (amount, telegram_id))
        await db.commit()

# ─── USERNAME GENERATOR ───────────────────────
from bot.words import generate_smart_username, nouns, adjectives
import random
import string

def generate_usernames(base_word: str, lang: str = 'uz', limit: int = 200) -> list:
    results = set()
    cat = base_word.strip().lower()
    
    # Qisqa so'zlarni tayyorlaymiz (5-6 harfli ma'noli so'zlar)
    if lang == 'uz':
        short_words = ["oltin", "kumush", "yulduz", "yigit", "yaxshi", "kuchli", "bahor", "quyosh", "osmon", "bulut", "orzu", "baxt", "shodlik", "vatan", "xalq", "yurak", "mehnat", "aqlli", "gozal", "shirin", "hayot", "dunyo", "zamon", "maktab", "ustoz", "olim", "bilim", "doira", "chiroy"]
    else:
        short_words = [w for w in nouns + adjectives if 5 <= len(w) <= 6]
        if not short_words:
            short_words = ["super", "smart", "tiger", "ninja", "coder", "gamer", "happy", "lucky"]
    
    while len(results) < limit * 2: # generate more to account for filtering
        if cat == 'qisqa':
            results.add(random.choice(short_words))
        else:
            results.add(generate_smart_username(lang=lang))
            
    valid = []
    import re
    for u in results:
        if 5 <= len(u) <= 32 and "__" not in u and re.match(r'^[a-zA-Z][a-zA-Z0-9_]*[a-zA-Z0-9]$', u):
            valid.append(u)
            
    random.shuffle(valid)
    return valid[:limit]

# ─── ASOSIY MENYU ─────────────────────────────
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Dasturni ochish", web_app=WebAppInfo(url=f"{WEB_URL}/app"))]
    ])

# ─── ROUTER VA HANDLERLAR ─────────────────────
router = Router()

# Foydalanuvchi holatlarini saqlash (oddiy dict, botni restart qilsa tozalanadi)
user_states = {}

import re

@router.channel_post()
async def auto_payment_handler(message: Message):
    try:
        channel_id = str(message.chat.id)
        target_channel_id = str(await get_setting("payment_channel_id", "0"))
        
        if target_channel_id != "0" and channel_id != target_channel_id:
            return
            
        text = message.text or message.caption or ""
        if not text:
            return
            
        clean_text = re.sub(r'[^0-9]', ' ', text)
        numbers = [int(n) for n in clean_text.split() if n.strip()]
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE topups SET status='expired' WHERE status='pending' AND created_at <= (strftime('%s','now') - 180)")
            await db.commit()
            
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id, telegram_id, expected_amount FROM topups WHERE status='pending'") as c:
                pending_topups = await c.fetchall()
                
            for topup in pending_topups:
                amt = int(topup['expected_amount'])
                if amt in numbers:
                    await db.execute("UPDATE topups SET status='completed' WHERE id=?", (topup['id'],))
                    await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (amt, topup['telegram_id']))
                    await db.commit()
                    
                    try:
                        await message.bot.send_message(
                            topup['telegram_id'], 
                            f"✅ <b>To'lov avtomatik qabul qilindi!</b>\n\nBalansingizga <b>{amt:,} so'm</b> qo'shildi.",
                            parse_mode="HTML"
                        )
                    except:
                        pass
                    
                    try:
                        await message.reply(f"✅ Tasdiqlandi (Topup ID: {topup['id']})")
                    except:
                        pass
                    break
    except Exception as e:
        logger.error(f"Auto-payment error: {e}")

@router.message(CommandStart())
async def start_cmd(message: Message):
    await create_user(message.from_user.id)

    from aiogram.types import FSInputFile
    banner = FSInputFile("static/welcome_banner.png")
    await message.answer_photo(
        photo=banner,
        caption=(
            f"👋 Salom, <b>{message.from_user.first_name}</b>!\n\n"
            f"🎯 <b>Usernamechi Bot</b>ga xush kelibsiz!\n\n"
            f"Bu bot orqali siz <b>qisqa, chiroyli va ma'noli</b> "
            f"Telegram usernamelarni avtomatik ravishda topib, "
            f"<b>sizning akkauntingizga</b> band qildirasiz.\n\n"
            f"⚡️ Tez • 🔒 Xavfsiz • 🎯 Aniq\n\n"
            f"👇 Quyidagi tugma orqali dasturni oching:"
        ),
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    token = get_admin_token(message.from_user.id)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Admin Panelga kirish", web_app=WebAppInfo(url=f"{WEB_URL}/admin?token={token}"))]
    ])
    await message.answer("Xush kelibsiz, Admin! 👑\nQuyidagi tugma orqali panelga kiring:", reply_markup=markup)


async def save_session(telegram_id, session_string):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET session_string=? WHERE telegram_id=?",
            (session_string, telegram_id)
        )
        await db.commit()

@router.message(F.photo)
async def photo_handler(message: Message):
    tid = message.from_user.id
    photo_id = message.photo[-1].file_id
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO payments (telegram_id, photo_id) VALUES (?, ?)", (tid, photo_id))
        await db.commit()
    
    await message.answer("✅ To'lov cheki qabul qilindi! Adminlar tekshirgach balansingizga pul qo'shiladi.")

@router.message(F.text)
async def text_handler(message: Message):
    user_id = message.from_user.id
    state   = user_states.get(user_id, {})

    if state.get("step") == "wait_session":
        session = message.text.strip()
        # Session string juda qisqa bo'lsa qabul qilmaymiz
        if len(session) < 50:
            await message.answer("❌ Bu session string emas. Iltimos, to'g'ri session string yuboring.")
            return
        # Session ni bazaga saqlaymiz
        await save_session(user_id, session)
        user_states.pop(user_id, None)
        await message.answer(
            "✅ <b>Akkaunt muvaffaqiyatli ulandi!</b>\n\n"
            "Endi '🛒 Username sotib olish' tugmasi orqali buyurtma bera olasiz.",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
        return

    if state.get("step") == "wait_category":
        user_states[user_id] = {"step": "wait_quantity", "category": message.text.strip()}
        await message.answer(
            f"✅ Kategoriya: <b>{message.text.strip()}</b>\n\n"
            f"Nechta username kerak? (1—10 ta)\n"
            f"💡 Narxi: <b>{USERNAME_PRICE:,} so'm/dona</b>",
            parse_mode="HTML"
        )

    elif state.get("step") == "wait_quantity":
        try:
            qty = int(message.text.strip())
            if not 1 <= qty <= 10:
                raise ValueError
        except ValueError:
            await message.answer("❌ 1 dan 10 gacha son kiriting!")
            return

        total   = qty * USERNAME_PRICE
        cat     = state["category"]
        user    = await get_user(user_id)
        balance = user["balance"] if user else 0

        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ Tasdiqlash ({total:,} so'm)", callback_data=f"order_{cat}_{qty}_{total}")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order_cancel")]
        ])
        await message.answer(
            f"📋 <b>Buyurtma tasdiqlash</b>\n\n"
            f"🏷 Kategoriya: <b>{cat}</b>\n"
            f"🔢 Miqdor: <b>{qty} ta</b>\n"
            f"💰 Narxi: <b>{total:,} so'm</b>\n"
            f"💳 Balansingiz: <b>{balance:,} so'm</b>\n\n"
            f"{'✅ Balans yetarli' if balance >= total else '❌ Balans yetarli emas. Avval to\'ldiring!'}",
            reply_markup=markup if balance >= total else None,
            parse_mode="HTML"
        )
        if balance < total:
            user_states.pop(user_id, None)

@router.callback_query(F.data == "order_cancel")
async def cancel_order(call: CallbackQuery):
    user_states.pop(call.from_user.id, None)
    await call.message.edit_text("❌ Buyurtma bekor qilindi.")

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders (telegram_id, category, quantity, price, status) VALUES (?,?,?,?,'processing')",
            (user_id, cat, qty, total)
        )
        order_id = cur.lastrowid
        await db.commit()

    user_states.pop(user_id, None)
    await call.message.edit_text(
        f"✅ Buyurtma qabul qilindi!\n\n"
        f"🏷 Kategoriya: <b>{cat}</b>\n"
        f"🔢 Miqdor: <b>{qty} ta</b>\n"
        f"💰 To'langan: <b>{total:,} so'm</b>\n\n"
        f"⏳ Bot hozir username qidirishni boshlaydi. Topilgan nomlar sizga xabar qilinadi!",
        parse_mode="HTML"
    )

    # Fon rejimida username qidirish boshlash
    asyncio.create_task(run_sniper(call.bot, user_id, order_id, cat, qty))

# ─── SNIPER ───────────────────────────────────
async def search_sniper(telegram_id: int, search_id: int, category: str, lang: str = 'uz'):
    """Fon rejimida faqat usernamesni tekshiradi va bazaga yozadi."""
    try:
        targets = generate_usernames(category, lang=lang, limit=200)
        found_count = 0
        
        user = await get_user(telegram_id)
        session_string = user["session_string"] if user else None
        
        if not session_string:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE search_tasks SET status='completed' WHERE id=?", (search_id,))
                await db.commit()
            return
            
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.errors import FloodWaitError, UsernameOccupiedError
        from telethon.tl.functions.account import CheckUsernameRequest
        
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        for username in targets:
            if found_count >= 50: # max 50 ta ko'rsatish
                break
            try:
                is_free = await client(CheckUsernameRequest(username=username))
                if is_free:
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("INSERT INTO search_results (search_id, username) VALUES (?,?)", (search_id, username))
                        await db.commit()
                    found_count += 1
                await asyncio.sleep(1) # FloodWait dan qochish
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except UsernameOccupiedError:
                pass
            except Exception as e:
                logger.error(f"Search xato: {e}")
                await asyncio.sleep(2)
                
        await client.disconnect()
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE search_tasks SET status='completed' WHERE id=?", (search_id,))
            await db.commit()
            
    except Exception as e:
        logger.error(f"Search task xato: {e}")

async def claim_sniper(bot, telegram_id: int, order_id: int, usernames: list):
    """Foydalanuvchi tanlagan aniq usernamelarni band qiladi."""
    try:
        user = await get_user(telegram_id)
        session_string = user["session_string"]
        
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.errors import FloodWaitError
        from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest, DeleteChannelRequest
        
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        claimed = []
        for username in usernames:
            try:
                ch = None
                try:
                    ch = await client(CreateChannelRequest(title=username.capitalize(), about="Usernamechi", megagroup=False))
                    ch_id = ch.chats[0].id
                    await client(UpdateUsernameRequest(channel=ch_id, username=username))
                    
                    claimed.append(username)
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("INSERT INTO registered_usernames (order_id, username) VALUES (?,?)", (order_id, username))
                        await db.execute("UPDATE orders SET registered_count=registered_count+1 WHERE id=?", (order_id,))
                        await db.commit()
                except Exception as inner_e:
                    if ch:
                        try:
                            await client(DeleteChannelRequest(channel=ch.chats[0].id))
                        except:
                            pass
                    if "ChannelsAdminPublicTooMuchError" in str(type(inner_e)):
                        await bot.send_message(telegram_id, "❌ <b>Diqqat:</b> Ommaviy link yaratish limiti tugagan! Jarayon to'xtatildi.", parse_mode="HTML")
                        break
                await asyncio.sleep(1)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except Exception as e:
                logger.error(f"Claim xato: {e}")
                
        await client.disconnect()
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status='completed' WHERE id=?", (order_id,))
            await db.commit()
            
        await bot.send_message(
            telegram_id,
            f"🎉 <b>Buyurtma yakunlandi!</b>\nJami band qilindi: <b>{len(claimed)} ta</b>\n"
            + ("\n".join(f"✅ @{u}" for u in claimed) if claimed else "❌ Hech qanday nom olinmadi."),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Claim task xato: {e}")

async def monitoring_loop(bot):
    """Orqa fonda barcha monitoring_tasks larni aylanib chiqadi."""
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.account import CheckUsernameRequest
    from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest, DeleteChannelRequest
    from telethon.errors import FloodWaitError
    
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT t.id, t.telegram_id, t.username, u.session_string FROM monitoring_tasks t JOIN users u ON t.telegram_id=u.telegram_id WHERE t.status='monitoring'") as c:
                    tasks = await c.fetchall()
            
            for task in tasks:
                if not task["session_string"]: continue
                try:
                    client = TelegramClient(StringSession(task["session_string"]), API_ID, API_HASH)
                    await client.connect()
                    
                    is_free = await client(CheckUsernameRequest(username=task["username"]))
                    if is_free:
                        ch = None
                        try:
                            ch = await client(CreateChannelRequest(title=task["username"].capitalize(), about="Monitored", megagroup=False))
                            ch_id = ch.chats[0].id
                            await client(UpdateUsernameRequest(channel=ch_id, username=task["username"]))
                            
                            async with aiosqlite.connect(DB_PATH) as db:
                                await db.execute("UPDATE monitoring_tasks SET status='claimed' WHERE id=?", (task["id"],))
                                await db.commit()
                                
                            try:
                                await bot.send_message(
                                    task["telegram_id"],
                                    f"🎯 <b>Nishon olindi!</b>\n\nKutgan usernamengiz bo'shadi va Siz uchun band qilindi: <b>@{task['username']}</b>",
                                    parse_mode="HTML"
                                )
                            except: pass
                        except Exception as inner_e:
                            if ch:
                                try: await client(DeleteChannelRequest(channel=ch.chats[0].id))
                                except: pass
                            if "ChannelsAdminPublicTooMuchError" in str(type(inner_e)):
                                async with aiosqlite.connect(DB_PATH) as db:
                                    await db.execute("UPDATE monitoring_tasks SET status='failed_limit' WHERE id=?", (task["id"],))
                                    await db.commit()
                                try:
                                    await bot.send_message(task["telegram_id"], f"❌ @{task['username']} bo'shadi, lekin ommaviy link limiti tugagani uchun ololmadim.")
                                except: pass
                    
                    await client.disconnect()
                except FloodWaitError as e:
                    await asyncio.sleep(e.seconds)
                except Exception:
                    pass
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Monitoring loop xato: {e}")
        await asyncio.sleep(300)

# ─── FASTAPI APP ──────────────────────────────
app = FastAPI()

# Static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Helper: Telegram initData verifikatsiya ────
def verify_init_data(init_data: str) -> dict | None:
    """Telegram WebApp init_data ni tekshiradi."""
    try:
        from urllib.parse import parse_qsl
        if not init_data: return None
        params = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = params.pop('hash', '')
        data_check = '\n'.join(f'{k}={v}' for k, v in sorted(params.items()))
        secret = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc_hash = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(calc_hash, received_hash):
            return None
            
        user_str = params.get('user', '{}')
        return json.loads(user_str)
    except:
        return None

def get_admin_token(telegram_id: int) -> str:
    secret = BOT_TOKEN + str(telegram_id)
    return hashlib.sha256(secret.encode()).hexdigest()[:32]

# ── Mini App Pages ─────────────────────────────
@app.get("/app", response_class=HTMLResponse)
async def mini_app():
    with open("static/app/index.html") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    with open("static/admin/index.html") as f:
        return f.read()

# ── Mini App API ───────────────────────────────
@app.get("/api/user")
async def api_user(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user:
        raise HTTPException(403, "Invalid init_data")
    tid = user['id']
    await create_user(tid)
    row = await get_user(tid)
    # Count stats
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM orders WHERE telegram_id=?", (tid,)) as c:
            total_orders = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM registered_usernames ru JOIN orders o ON ru.order_id=o.id WHERE o.telegram_id=?", (tid,)) as c:
            total_usernames = (await c.fetchone())[0]
    return {"balance": row["balance"] if row else 0, 
            "free_searches": row.get("free_searches", 1) if row else 1,
            "session_string": bool(row["session_string"]) if row else False,
            "total_orders": total_orders, "total_usernames": total_usernames}

@app.get("/api/card")
async def api_card():
    card = await get_setting("payment_card", "")
    return {"card": card}

@app.post("/api/topup/request")
async def api_topup_request(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user:
        raise HTTPException(403)
    tid = user['id']
    amount = int(data.get('amount', 0))
    if amount < 1000:
        return {"ok": False, "error": "Eng kamida 1,000 so'm"}
    
    # Generate unique amount (add 1 to 99 tiyin)
    async with aiosqlite.connect(DB_PATH) as db:
        # Eski to'lovlarni avtomatik muddati o'tgan deb belgilaymiz (180 soniya = 3 daqiqa)
        await db.execute("UPDATE topups SET status='expired' WHERE status='pending' AND created_at <= (strftime('%s','now') - 180)")
        await db.commit()
        
        for _ in range(100):
            unique_amount = amount + random.randint(1, 99)
            async with db.execute("SELECT id FROM topups WHERE expected_amount=? AND status='pending'", (unique_amount,)) as c:
                if not await c.fetchone():
                    # Unikal summa topildi
                    await db.execute("INSERT INTO topups (telegram_id, expected_amount) VALUES (?, ?)", (tid, unique_amount))
                    await db.commit()
                    return {"ok": True, "amount": unique_amount, "expires_in": 180}
    
    return {"ok": False, "error": "Bandlik yuqori, keyinroq urining"}

@app.get("/api/orders")
async def api_orders(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user:
        raise HTTPException(403)
    tid = user['id']
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders WHERE telegram_id=? ORDER BY id DESC LIMIT 20", (tid,)) as c:
            orders = [dict(o) for o in await c.fetchall()]
        for o in orders:
            async with db.execute("SELECT username FROM registered_usernames WHERE order_id=?", (o['id'],)) as c:
                o['usernames'] = [r[0] for r in await c.fetchall()]
    return orders

@app.post("/api/monitor/start")
async def api_monitor_start(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    username = data.get('username','').strip().replace('@', '').lower()
    
    if not username or len(username) < 5:
        return {"ok": False, "error": "Noto'g'ri username"}
        
    row = await get_user(tid)
    if not row or not row['session_string']:
        return {"ok": False, "error": "Akkaunt ulanmagan"}
        
    price = 10000 # Kafolat puli (monitor qilish uchun)
    if (row['balance'] or 0) < price:
        return {"ok": False, "error": f"Balans yetarli emas (Kerak: {price:,} so'm)"}
        
    await deduct_balance(tid, price)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO monitoring_tasks (telegram_id, username) VALUES (?,?)", (tid, username))
        await db.commit()
    return {"ok": True}

@app.get("/api/monitor/list")
async def api_monitor_list(init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM monitoring_tasks WHERE telegram_id=? ORDER BY id DESC", (user['id'],)) as c:
            tasks = [dict(r) for r in await c.fetchall()]
    return {"ok": True, "tasks": tasks}

@app.post("/api/search/start")
async def api_search_start(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user:
        raise HTTPException(403)
    tid = user['id']
    cat = data.get('category','').strip()
    lang = data.get('lang', 'uz')
    qty = int(data.get('quantity', 1))
    qty = max(1, min(10, qty))  # 1-10 oralig'ida cheklash

    if not cat:
        return {"ok": False, "error": "Kategoriya kiritilmadi"}

    row = await get_user(tid)
    if not row or not row['session_string']:
        return {"ok": False, "error": "Akkaunt ulanmagan"}

    total_price = max(0, (qty - row.get('free_searches', 1)) * 5000)
    if (row['balance'] or 0) < total_price:
        return {"ok": False, "error": f"Balans yetarli emas ({total_price:,} so'm kerak)"}

    # Oldindan pulni va bepul urinishni yechib olamiz
    if total_price > 0:
        await deduct_balance(tid, total_price)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET free_searches = MAX(0, free_searches - ?) WHERE telegram_id = ?", (qty, tid))
        await db.commit()

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO search_tasks (telegram_id, category, paid_qty, lang) VALUES (?, ?, ?, ?)",
            (tid, cat, qty, lang)
        )
        search_id = cur.lastrowid
        await db.commit()

    asyncio.create_task(search_sniper(tid, search_id, cat, lang=lang))
    return {"ok": True, "search_id": search_id, "paid_qty": qty, "charged": total_price}

@app.post("/api/search/refresh")
async def api_search_refresh(request: Request):
    """Balansdan pul yechmasdan yangi qidiruv boshlaydi (foydalanuvchi allaqachon to'lagan)."""
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    search_id = int(data.get('search_id', 0))

    row = await get_user(tid)
    if not row or not row['session_string']:
        return {"ok": False, "error": "Akkaunt ulanmagan"}

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT category, paid_qty, lang FROM search_tasks WHERE id=? AND telegram_id=?", (search_id, tid)) as c:
            task = await c.fetchone()
            if not task:
                return {"ok": False, "error": "Topilmadi"}
            cat = task[0]
            paid_qty = task[1]
            lang = task[2]
            
        await db.execute("UPDATE search_tasks SET status='searching' WHERE id=?", (search_id,))
        await db.commit()
        
    asyncio.create_task(search_sniper(tid, search_id, cat, lang=lang))
    return {"ok": True, "search_id": search_id}

@app.get("/api/search/results")
async def api_search_results(search_id: int, init_data: str = ""):
    user = verify_init_data(init_data)
    if not user: raise HTTPException(403)
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Holatni tekshiramiz
        async with db.execute("SELECT status FROM search_tasks WHERE id=? AND telegram_id=?", (search_id, user['id'])) as c:
            task = await c.fetchone()
            if not task:
                return {"ok": False, "error": "Topilmadi"}
                
        async with db.execute("SELECT id, username, status FROM search_results WHERE search_id=? ORDER BY id ASC", (search_id,)) as c:
            results = [dict(r) for r in await c.fetchall()]
            
        return {"ok": True, "status": task['status'], "results": results}

@app.post("/api/buy_selected")
async def api_buy_selected(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    
    usernames = data.get('usernames', [])
    search_id = data.get('search_id')
    qty = len(usernames)
    
    if not usernames or qty > 10:
        return {"ok": False, "error": "1 dan 10 tagacha tanlang"}
        
    row = await get_user(tid)
    price_per_item = int(await get_setting("username_price", 5000))
    price = qty * price_per_item
    
    if (row['balance'] or 0) < price:
        return {"ok": False, "error": f"Balans yetarli emas (Kerak: {price:,} so'm)"}
        
    # Pulni yechish va order yaratish
    await deduct_balance(tid, price)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO orders (telegram_id, category, quantity, price, status) VALUES (?,?,?,?,'processing')",
                               (tid, f"Tanlangan ({qty})", qty, price))
        order_id = cur.lastrowid
        
        # Natijalarni claimed holatga o'tkazish
        for u in usernames:
            await db.execute("UPDATE search_results SET status='claimed' WHERE search_id=? AND username=?", (search_id, u))
        await db.commit()
        
    bot_instance = Bot(token=BOT_TOKEN)
    asyncio.create_task(claim_sniper(bot_instance, tid, order_id, usernames))
    return {"ok": True}

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

auth_clients = {}

@app.post("/api/auth/send_code")
async def auth_send_code(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    phone = data.get('phone', '').strip().replace('+', '')
    if not phone: return {"ok": False, "error": "Telefon kiritilmadi"}
    
    if tid in auth_clients:
        try: await auth_clients[tid]['client'].disconnect()
        except: pass
        del auth_clients[tid]
        
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        auth_clients[tid] = {
            "client": client,
            "phone": phone,
            "phone_code_hash": sent.phone_code_hash
        }
        return {"ok": True}
    except Exception as e:
        await client.disconnect()
        return {"ok": False, "error": str(e)}

@app.post("/api/auth/login")
async def auth_login(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    code = data.get('code', '').strip()
    
    if tid not in auth_clients:
        return {"ok": False, "error": "Avval telefon kiritilmagan yoki seans muddati tugagan"}
        
    state = auth_clients[tid]
    client = state['client']
    try:
        await client.sign_in(phone=state['phone'], code=code, phone_code_hash=state['phone_code_hash'])
    except SessionPasswordNeededError:
        return {"ok": True, "need_password": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
        
    session_string = client.session.save()
    await client.disconnect()
    del auth_clients[tid]
    await save_session(tid, session_string)
    return {"ok": True, "success": True}

@app.post("/api/auth/password")
async def auth_password(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user: raise HTTPException(403)
    tid = user['id']
    password = data.get('password', '')
    
    if tid not in auth_clients:
        return {"ok": False, "error": "Seans muddati tugagan"}
        
    state = auth_clients[tid]
    client = state['client']
    try:
        await client.sign_in(password=password)
    except Exception as e:
        return {"ok": False, "error": str(e)}
        
    session_string = client.session.save()
    await client.disconnect()
    del auth_clients[tid]
    await save_session(tid, session_string)
    return {"ok": True, "success": True}

@app.post("/api/session/disconnect")
async def api_disconnect(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user:
        raise HTTPException(403)
    await save_session(user['id'], None)
    return {"ok": True}

@app.get("/api/admin/settings")
async def api_admin_settings_get(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    card = await get_setting("payment_card", "")
    channel = await get_setting("payment_channel_id", "")
    price = await get_setting("username_price", "5000")
    return {"payment_card": card, "payment_channel_id": channel, "username_price": price}

@app.post("/api/admin/settings")
async def api_admin_settings_set(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    
    data = await request.json()
    if 'payment_card' in data:
        await set_setting("payment_card", data['payment_card'])
    if 'payment_channel_id' in data:
        await set_setting("payment_channel_id", data['payment_channel_id'])
    if 'username_price' in data:
        await set_setting("username_price", data['username_price'])
    return {"ok": True}

# ── Admin API ──────────────────────────────────
@app.get("/api/admin/auth")
async def admin_auth(request: Request):
    """Telegram Login Widget orqali kirish"""
    params = dict(request.query_params)
    if not params:
        # Bot ga redirect qilamiz
        return RedirectResponse(f"https://t.me/{(await Bot(token=BOT_TOKEN).get_me()).username}?start=admin")
    tid = int(params.get('id', 0))
    if tid not in ADMIN_IDS:
        return HTMLResponse("<h2>Ruxsat yo'q</h2>", status_code=403)
    token = get_admin_token(tid)
    return RedirectResponse(f"/admin?token={token}")

@app.get("/api/admin/check")
async def admin_check(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token:
            return {"ok": True}
    raise HTTPException(403, "Ruxsat yo'q")

@app.get("/api/admin/stats")
async def admin_stats(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token:
            break
    else:
        raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        orders = (await (await db.execute("SELECT COUNT(*) FROM orders")).fetchone())[0]
        usernames = (await (await db.execute("SELECT COUNT(*) FROM registered_usernames")).fetchone())[0]
        revenue = (await (await db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='approved'")).fetchone())[0]
        # Last 7 days
        labels, d_revenue, d_orders, d_users = [], [], [], []
        for i in range(6,-1,-1):
            ts_start = time.time() - i*86400
            ts_end = ts_start + 86400
            day = time.strftime('%d/%m', time.localtime(ts_start))
            r = (await (await db.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='approved' AND created_at>=? AND created_at<?", (ts_start,ts_end))).fetchone())[0]
            o = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE rowid>=? AND rowid<?", (0,9999))).fetchone())[0]
            u = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
            labels.append(day); d_revenue.append(r); d_orders.append(o); d_users.append(u)
    return {"users":users,"orders":orders,"usernames":usernames,"revenue":revenue,
            "daily_labels":labels,"daily_revenue":d_revenue,"daily_orders":d_orders,"daily_users":d_users}

@app.get("/api/admin/payments")
async def admin_payments(status: str = "", x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM payments" + (" WHERE status=?" if status else "") + " ORDER BY id DESC LIMIT 50"
        args = (status,) if status else ()
        async with db.execute(q, args) as c:
            return [dict(r) for r in await c.fetchall()]

@app.post("/api/admin/payment/approve")
async def admin_approve(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    pid = data['payment_id']; tid = data['telegram_id']; amt = data['amount']
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status='approved', amount=? WHERE id=?", (amt, pid))
        await db.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (amt, tid))
        await db.commit()
    bot_instance = Bot(token=BOT_TOKEN)
    try:
        await bot_instance.send_message(tid, f"🎉 Balansingiz <b>{amt:,} so'm</b>ga to'ldirildi!", parse_mode="HTML")
    finally:
        await bot_instance.session.close()
    return {"ok": True}

@app.post("/api/admin/payment/reject")
async def admin_reject(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    pid = data['payment_id']; tid = data['telegram_id']
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE payments SET status='rejected' WHERE id=?", (pid,))
        await db.commit()
    bot_instance = Bot(token=BOT_TOKEN)
    try:
        await bot_instance.send_message(tid, "❌ To'lovingiz rad etildi.")
    finally:
        await bot_instance.session.close()
    return {"ok": True}

@app.get("/api/admin/users")
async def admin_users(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT u.*, (SELECT COUNT(*) FROM orders WHERE telegram_id=u.telegram_id) as order_count FROM users u ORDER BY id DESC") as c:
            return [dict(r) for r in await c.fetchall()]

@app.post("/api/admin/user/balance")
async def admin_set_balance(request: Request, x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    data = await request.json()
    amt = data['amount']
    tid = data['telegram_id']
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=? WHERE telegram_id=?", (amt, tid))
        await db.commit()
    
    # Foydalanuvchiga xabar yuborish
    bot_instance = Bot(token=BOT_TOKEN)
    try:
        await bot_instance.send_message(
            tid, 
            f"💰 Admin tomonidan balansingiz tahrirlandi!\nJoriy balans: <b>{amt:,} so'm</b>", 
            parse_mode="HTML"
        )
    except:
        pass
    finally:
        await bot_instance.session.close()

    return {"ok": True}

@app.get("/api/admin/orders")
async def admin_orders(x_admin_token: str = Header(default="")):
    for aid in ADMIN_IDS:
        if get_admin_token(aid) == x_admin_token: break
    else: raise HTTPException(403)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 100") as c:
            return [dict(r) for r in await c.fetchall()]

# ─── MAIN ─────────────────────────────────────
async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher()
    dp.include_router(router)
    logger.info("🤖 Bot + 🌐 Web ishga tushdi!")
    
    # Orqa fonda monitoring loop ni ishga tushiramiz
    asyncio.create_task(monitoring_loop(bot))

    # Aiogram bot va FastAPI parallel ishlatish
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="warning")
    server = uvicorn.Server(config)

    await asyncio.gather(
        dp.start_polling(bot),
        server.serve()
    )

if __name__ == "__main__":
    asyncio.run(main())
