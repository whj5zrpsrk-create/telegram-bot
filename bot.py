import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8882857235:AAEpU6Ikamvyb4_0O5uSXgldDJEp5AIhSX8"

# Majburiy obuna kanali
CHANNEL_USERNAME = "@oneway_gr"
CHANNEL_URL = "https://t.me/oneway_gr"
# ====================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- 1. MA'LUMOTLAR BAZASINI YARATISH ---
def init_db():
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            code TEXT PRIMARY KEY,
            file_id TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_movie(code: str, file_id: str):
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO movies (code, file_id) VALUES (?, ?)", (code, file_id))
    conn.commit()
    conn.close()

def get_movie(code: str):
    conn = sqlite3.connect("movies.db")
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM movies WHERE code = ?", (code,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


# --- 2. OBUNANI TEKSHIRISH FUNKSIYASI ---
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except TelegramBadRequest:
        return False


# --- 3. OBUNA UCHUN TUGMALAR ---
def get_subscription_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Obuna bo'lish", url=CHANNEL_URL))
    builder.row(types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
    builder.row(types.InlineKeyboardButton(text="💎 Premium", callback_data="premium"))
    return builder.as_markup()


# --- 4. START VA CALLBACKLAR ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        await message.answer(
            "📢 Botdan foydalanish uchun avval quyidagi kanalga obuna bo'ling:",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    name = message.from_user.first_name if message.from_user.first_name else "Foydalanuvchi"
    await message.answer(
        f"Salom, {name}!\n\n🎬 Istalgan kino kodini yuboring:"
    )

@dp.callback_query(lambda c: c.data == "check_sub")
async def process_check_sub(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if is_subscribed:
        await callback.message.edit_text(
            "Rahmat! Obuna tasdiqlandi ✅\n\n🎬 Endi kino kodini yuborishingiz mumkin:"
        )
    else:
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)

@dp.callback_query(lambda c: c.data == "premium")
async def process_premium(callback: types.CallbackQuery):
    await callback.answer("💎 Premium tez orada ishga tushadi!", show_alert=True)


# --- 5. KANALGA YANGI POST TASHLANGANDA AVTO-SAQLASH ---
@dp.channel_post()
async def channel_post_handler(message: types.Message):
    if message.video and message.caption:
        code = message.caption.strip()
        file_id = message.video.file_id
        save_movie(code, file_id)
        logging.info(f"Yangi kino bazaga saqlandi -> Kod: {code}")


# --- 6. ESKI KINOLARNI BOTGA FORWARD QILIB SAQLASH YOKI KOD ORQALI QIDIRISH ---@dp.message()
async def message_handler(message: types.Message):
    user_id = message.from_user.id
    
    # Agar foydalanuvchi (admin sifatida) yopiq kanaldan videoni botga forward qilsa
    if message.video and message.caption:
        code = message.caption.strip()
        file_id = message.video.file_id
        save_movie(code, file_id)
        await message.answer(f"✅ Eski kino bazaga qo'shildi! Kod: {code}")
        return

    # Obunani tekshirish
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        await message.answer(
            "📢 Botdan foydalanish uchun avval kanalga obuna bo'ling:",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    # Kod bo'yicha kinoni qidirish
    if not message.text:
        await message.answer("❌ Iltimos, kino kodini raqam ko'rinishida yuboring (masalan: 1):")
        return
    
    code = message.text.strip()
    file_id = get_movie(code)
    
    if file_id:
        try:
            await message.answer_video(
                video=file_id,
                caption=f"🎬 Siz so'ragan kino!\n🔢 Kodi: {code}"
            )
        except Exception as e:
            logging.error(f"Kinoni yuborishda xatolik: {e}")
            await message.answer("❌ Bu kinoni yuborishda xatolik yuz berdi.")
    else:
        await message.answer(
            "❌ Kechirasiz, bu kod bo'yicha hech qanday kino topilmadi.\nKodni to'g'ri kiritganingizni tekshiring:"
        )


# --- 7. BOTNI ISHGA TUSHIRISH ---
import asyncio

async def main():
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())