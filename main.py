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
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import CommandStart
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
DB_PATH       = "saas.db"
WEB_URL       = os.getenv("WEB_HOST", "http://localhost:8000")

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
                session_string TEXT
            )
        """)
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
        await db.commit()
        # Sozlamalarni kiritish
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_card', '8600123456789012')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('payment_channel_id', '0')")
        await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('username_price', '5000')")
        await db.commit()
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
            return await cur.fetchone()

async def create_user(telegram_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (telegram_id,))
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
def generate_usernames(base_word: str, limit: int = 200) -> list:
    base = base_word.lower().replace(" ", "").replace("@", "")
    suffixes = ["chi", "lar", "lash", "im", "iy", "uz", "go",
                "uzb", "pro", "bot", "er", "jon", "bek", "off",
                "official", "real", "hub", "zone", "net", "city"]
    prefixes = ["uz", "the", "my", "pro", "best", "top", "super",
                "ultra", "smart", "mega"]
    results = set()
    results.add(base)
    for suf in suffixes:
        results.add(f"{base}{suf}")
    for pref in prefixes:
        results.add(f"{pref}{base}")
        results.add(f"{pref}_{base}")
    for suf in suffixes:
        for pref in prefixes[:4]:
            results.add(f"{pref}{base}{suf}")
    # Faqat 5+ harflilarni va maximal 32 ta harflilarni olamiz
    valid = [u for u in results if 5 <= len(u) <= 32]
    random.shuffle(valid)
    return valid[:limit]

# ─── ASOSIY MENYU ─────────────────────────────
def main_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💰 Balans"), KeyboardButton(text="💳 To'ldirish")],
        [KeyboardButton(text="🛒 Username sotib olish")],
        [KeyboardButton(text="🔗 Akkaunt ulash"), KeyboardButton(text="📋 Buyurtmalarim")]
    ], resize_keyboard=True)

# ─── ROUTER VA HANDLERLAR ─────────────────────
router = Router()

# Foydalanuvchi holatlarini saqlash (oddiy dict, botni restart qilsa tozalanadi)
user_states = {}

@router.message(CommandStart())
async def start_cmd(message: Message):
    await create_user(message.from_user.id)
    user = await get_user(message.from_user.id)
    await message.answer(
        f"👋 Xush kelibsiz, <b>{message.from_user.first_name}</b>!\n\n"
        f"Bu bot orqali <b>qisqa va ma'noli</b> Telegram usernamelarni "
        f"avtomatik band qilib olishingiz mumkin.\n\n"
        f"💰 Balansingiz: <b>{user['balance'] if user else 0:,} so'm</b>\n"
        f"💡 1 ta username = <b>{USERNAME_PRICE:,} so'm</b>",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

@router.message(F.text == "💰 Balans")
async def balance_cmd(message: Message):
    await create_user(message.from_user.id)
    user = await get_user(message.from_user.id)
    await message.answer(
        f"💰 Balansingiz: <b>{user['balance']:,} so'm</b>\n\n"
        f"To'ldirish uchun '💳 To'ldirish' tugmasini bosing.",
        parse_mode="HTML"
    )

@router.message(F.text == "💳 To'ldirish")
async def topup_cmd(message: Message):
    await message.answer(
        f"💳 <b>Balansni to'ldirish</b>\n\n"
        f"Karta raqamimizga to'lov qiling:\n"
        f"<code>{PAYMENT_CARD}</code>\n\n"
        f"To'lov qilgach, chek rasmini (screenshot) shu yerga yuboring. "
        f"Admin tasdiqlashi bilan balansingiz to'ldiriladi.",
        parse_mode="HTML"
    )

@router.message(F.text == "🔗 Akkaunt ulash")
async def link_account_cmd(message: Message):
    user = await get_user(message.from_user.id)
    if user and user["session_string"]:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangi session bilan almashtirish", callback_data="replace_session")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_session")]
        ])
        await message.answer(
            "✅ Akkauntingiz allaqachon ulangan!\n\n"
            "Yangi session bilan almashtirishni xohlaysizmi?",
            reply_markup=markup
        )
    else:
        user_states[message.from_user.id] = {"step": "wait_session"}
        await message.answer(
            "🔗 <b>Akkaunt ulash</b>\n\n"
            "Username band qilish uchun Telegram akkauntingizni ulashingiz kerak.\n\n"
            "<b>Session String qanday olish mumkin:</b>\n"
            "1️⃣ @StringSessionBot botiga kiring\n"
            "2️⃣ /generate buyrug'ini yuboring\n"
            "3️⃣ API ID va API HASH kiriting (my.telegram.org dan)\n"
            "4️⃣ Telefon raqamingizni kiriting\n"
            "5️⃣ SMS kodni kiriting\n"
            "6️⃣ Bot sizga uzun session string beradi\n\n"
            "✉️ <b>Endi o'sha session stringni shu yerga yuboring:</b>",
            parse_mode="HTML"
        )

@router.callback_query(F.data == "replace_session")
async def replace_session_cb(call: CallbackQuery):
    user_states[call.from_user.id] = {"step": "wait_session"}
    await call.message.edit_text(
        "✉️ Yangi session stringni yuboring:"
    )

@router.callback_query(F.data == "cancel_session")
async def cancel_session_cb(call: CallbackQuery):
    await call.message.edit_text("❌ Bekor qilindi.")

@router.message(F.text == "🛒 Username sotib olish")
async def buy_username_cmd(message: Message):
    user = await get_user(message.from_user.id)
    if not user or not user["session_string"]:
        await message.answer(
            "⚠️ Avval akkauntingizni ulang!\n\n"
            "'🔗 Akkaunt ulash' tugmasini bosing."
        )
        return
    user_states[message.from_user.id] = {"step": "wait_category"}
    price = int(await get_setting("username_price", 5000))
    await message.answer(
        f"🎯 <b>Username kategoriyasini kiriting</b>\n\n"
        f"Misol: <code>dastur</code>, <code>kino</code>, <code>biznes</code>, <code>savdo</code>\n\n"
        f"Bot shu so'z asosida ko'plab variantlar yasab, bo'shlarini band qiladi.\n\n"
        f"💵 1 ta username narxi: <b>{price:,} so'm</b>",
        parse_mode="HTML"
    )

@router.message(F.text == "📋 Buyurtmalarim")
async def my_orders_cmd(message: Message):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM orders WHERE telegram_id=? ORDER BY id DESC LIMIT 10",
            (message.from_user.id,)
        ) as cur:
            orders = await cur.fetchall()

    if not orders:
        await message.answer("📋 Hozircha buyurtmalaringiz yo'q.")
        return

    text = "📋 <b>So'nggi buyurtmalaringiz:</b>\n\n"
    for o in orders:
        status_icon = {"pending": "⏳", "processing": "🔄", "completed": "✅"}.get(o["status"], "❓")
        text += (f"{status_icon} #{o['id']} — <b>{o['category']}</b>\n"
                 f"   {o['registered_count']}/{o['quantity']} ta | {o['price']:,} so'm\n\n")
    await message.answer(text, parse_mode="HTML")

@router.message(F.photo)
async def handle_payment_photo(message: Message):
    user_id = message.from_user.id
    caption = (
        f"💰 Yangi to'lov cheki!\n"
        f"Foydalanuvchi ID: {user_id}\n"
        f"Ism: {message.from_user.full_name}\n\n"
        f"Summani tasdiqlang:"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ 10,000 so'm",  callback_data=f"pay_{user_id}_10000")],
        [InlineKeyboardButton(text="✅ 25,000 so'm",  callback_data=f"pay_{user_id}_25000")],
        [InlineKeyboardButton(text="✅ 50,000 so'm",  callback_data=f"pay_{user_id}_50000")],
        [InlineKeyboardButton(text="✅ 100,000 so'm", callback_data=f"pay_{user_id}_100000")],
        [InlineKeyboardButton(text="❌ Rad etish",    callback_data=f"pay_reject_{user_id}")]
    ])
    try:
        await message.bot.send_photo(
            chat_id=ADMIN_CHANNEL,
            photo=message.photo[-1].file_id,
            caption=caption,
            reply_markup=markup
        )
        await message.answer("✅ Chek adminga yuborildi! Tasdiqlangach, balansingiz to'ldiriladi.")
    except Exception as e:
        logger.error(f"Admin kanalga yuborishda xato: {e}")
        await message.answer("❌ Xato yuz berdi. Admin kanalini tekshiring.")

@router.callback_query(F.data.startswith("pay_reject_"))
async def reject_payment(call: CallbackQuery):
    user_id = int(call.data.split("_")[2])
    await call.message.edit_caption(caption="❌ To'lov rad etildi.")
    await call.bot.send_message(user_id, "❌ To'lovingiz rad etildi. Muammo bo'lsa adminga murojaat qiling.")

@router.callback_query(F.data.startswith("pay_"))
async def approve_payment(call: CallbackQuery):
    parts = call.data.split("_")
    if parts[1] == "reject":
        return
    user_id = int(parts[1])
    amount  = int(parts[2])
    await update_balance(user_id, amount)
    await call.message.edit_caption(caption=f"✅ {amount:,} so'm tasdiqlandi va balansi to'ldirildi.")
    await call.bot.send_message(user_id, f"🎉 Balansingiz <b>{amount:,} so'm</b>ga to'ldirildi!", parse_mode="HTML")

async def save_session(telegram_id, session_string):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET session_string=? WHERE telegram_id=?",
            (session_string, telegram_id)
        )
        await db.commit()

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
async def run_sniper(bot, telegram_id: int, order_id: int, category: str, quantity: int):
    """Fon rejimida username qidirib band qiladi (Telethon sessiyasiz demo)"""
    try:
        targets = generate_usernames(category, limit=quantity * 20)
        found   = []

        user = await get_user(telegram_id)
        session_string = user["session_string"] if user else None

        if not session_string:
            # Session yo'q — faqat variantlarni ko'rsatamiz
            sample = targets[:quantity * 2]
            result_text = (
                f"ℹ️ <b>Diqqat:</b> Siz hali akkauntingizni ulamadingiz.\n\n"
                f"<b>{category}</b> uchun mumkin bo'lgan usernamelar:\n"
                + "\n".join(f"• @{u}" for u in sample[:20])
                + f"\n\n<i>Ularni band qilish uchun akkauntingizni ulang.</i>"
            )
            await bot.send_message(telegram_id, result_text, parse_mode="HTML")
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("UPDATE orders SET status='completed' WHERE id=?", (order_id,))
                await db.commit()
            return

        # Telethon bilan qidirish
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from telethon.errors import FloodWaitError, UsernameOccupiedError
        from telethon.tl.functions.account import CheckUsernameRequest
        from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest

        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()

        for username in targets:
            if len(found) >= quantity:
                break
            try:
                is_free = await client(CheckUsernameRequest(username=username))
                if is_free:
                    ch = await client(CreateChannelRequest(title=username.capitalize(), about="", megagroup=False))
                    ch_id = ch.chats[0].id
                    await client(UpdateUsernameRequest(channel=ch_id, username=username))
                    found.append(username)

                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute(
                            "INSERT INTO registered_usernames (order_id, username) VALUES (?,?)",
                            (order_id, username)
                        )
                        await db.execute(
                            "UPDATE orders SET registered_count=registered_count+1 WHERE id=?",
                            (order_id,)
                        )
                        await db.commit()

                    await bot.send_message(
                        telegram_id,
                        f"✅ @{username} band qilindi! ({len(found)}/{quantity})",
                        parse_mode="HTML"
                    )
                await asyncio.sleep(1)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
            except UsernameOccupiedError:
                pass
            except Exception as e:
                logger.error(f"Sniper xato: {e}")
                await asyncio.sleep(2)

        await client.disconnect()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE orders SET status='completed' WHERE id=?", (order_id,))
            await db.commit()

        await bot.send_message(
            telegram_id,
            f"🎉 <b>Buyurtma yakunlandi!</b>\n\n"
            f"Jami band qilindi: <b>{len(found)}/{quantity} ta</b>\n"
            + ("\n".join(f"✅ @{u}" for u in found) if found else "❌ Hech qanday bo'sh username topilmadi."),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Sniper run error: {e}")

# ─── FASTAPI APP ──────────────────────────────
app = FastAPI()

# Static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ── Helper: Telegram initData verifikatsiya ────
def verify_init_data(init_data: str) -> dict | None:
    """Telegram WebApp init_data ni tekshiradi."""
    try:
        params = dict(p.split('=', 1) for p in init_data.split('&') if '=' in p)
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
    return {"balance": row["balance"] if row else 0, "session_string": bool(row["session_string"]) if row else False,
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
        for _ in range(100):
            unique_amount = amount + random.randint(1, 99)
            async with db.execute("SELECT id FROM topups WHERE expected_amount=? AND status='pending'", (unique_amount,)) as c:
                if not await c.fetchone():
                    # Unikal summa topildi
                    await db.execute("INSERT INTO topups (telegram_id, expected_amount) VALUES (?, ?)", (tid, unique_amount))
                    await db.commit()
                    return {"ok": True, "amount": unique_amount}
    
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

@app.post("/api/order")
async def api_order(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user:
        raise HTTPException(403)
    tid = user['id']
    cat = data.get('category','').strip()
    qty = int(data.get('quantity', 1))
    if not cat or not 1 <= qty <= 10:
        return {"ok": False, "error": "Noto'g'ri ma'lumot"}
    row = await get_user(tid)
    if not row or not row['session_string']:
        return {"ok": False, "error": "Akkaunt ulanmagan"}
    
    price_per_item = int(await get_setting("username_price", 5000))
    price = qty * price_per_item
    
    if (row['balance'] or 0) < price:
        return {"ok": False, "error": "Balans yetarli emas"}
    await deduct_balance(tid, price)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("INSERT INTO orders (telegram_id,category,quantity,price,status) VALUES (?,?,?,?,'processing')",
                               (tid, cat, qty, price))
        order_id = cur.lastrowid
        await db.commit()
    bot_instance = Bot(token=BOT_TOKEN)
    asyncio.create_task(run_sniper(bot_instance, tid, order_id, cat, qty))
    return {"ok": True}

@app.post("/api/session")
async def api_session(request: Request):
    data = await request.json()
    user = verify_init_data(data.get('init_data',''))
    if not user:
        raise HTTPException(403)
    session = data.get('session_string','').strip()
    if len(session) < 50:
        return {"ok": False, "error": "Session string juda qisqa"}
    await save_session(user['id'], session)
    return {"ok": True}

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
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET balance=? WHERE telegram_id=?", (data['amount'], data['telegram_id']))
        await db.commit()
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

    # Aiogram bot va FastAPI parallel ishlatish
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="warning")
    server = uvicorn.Server(config)

    await asyncio.gather(
        dp.start_polling(bot),
        server.serve()
    )

if __name__ == "__main__":
    asyncio.run(main())
