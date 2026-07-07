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
import aiosqlite

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.filters import CommandStart
from dotenv import load_dotenv

load_dotenv()

# ─── SOZLAMALAR ──────────────────────────────
BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
ADMIN_CHANNEL = int(os.getenv("ADMIN_CHANNEL", "0"))
PAYMENT_CARD  = os.getenv("PAYMENT_CARD", "")
API_ID        = int(os.getenv("API_ID", "0"))
API_HASH      = os.getenv("API_HASH", "")
DB_PATH       = "saas.db"
USERNAME_PRICE = 5000  # 1 ta username narxi (so'm)

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
        await db.commit()
    logger.info("✅ Baza tayyor")

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
        f"Bu bot orqali <b>qisqa va ma'noli</b> Telegram usernamalarini "
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
    await message.answer(
        "🎯 <b>Username kategoriyasini kiriting</b>\n\n"
        "Misol: <code>dastur</code>, <code>kino</code>, <code>biznes</code>, <code>savdo</code>\n\n"
        "Bot shu so'z asosida ko'plab variantlar yasab, bo'shlarini band qiladi.",
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

@router.callback_query(F.data.startswith("order_"))
async def confirm_order(call: CallbackQuery):
    parts = call.data.split("_")
    cat   = parts[1]
    qty   = int(parts[2])
    total = int(parts[3])
    user_id = call.from_user.id

    user = await get_user(user_id)
    if not user or user["balance"] < total:
        await call.answer("❌ Balans yetarli emas!", show_alert=True)
        return

    await deduct_balance(user_id, total)
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

# ─── MAIN ─────────────────────────────────────
async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher()
    dp.include_router(router)
    logger.info("🤖 Bot ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
