import logging
import gspread
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8882857235:AAEpU6Ikamvyb4_0O5uSXgldDJEp5AIhSX8"

# 3 ta majburiy obuna kanallari
CHANNELS = [
    {
        "id": -1003545290418, 
        "url": "https://t.me/+nPpk9AOwIvhmYzIy"
    },
    {
        "id": -1002373169167, 
        "url": "https://t.me/+UWXH1a423ihkYTEy"
    },
    {
        "id": -1003343553289, 
        "url": "https://t.me/+uqohbvcdF1k4ZWZi"
    }
]

# Google Sheets havolasi
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1SgcywJFP3j6AvHXl4yZr71-dO9niF7dKGELBG3INoYg/edit?usp=sharing"
# ====================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- GOOGLE SHEETS BAZASINI ULASH ---
gc = gspread.service_account(filename="credentials.json")
sheet = gc.open_by_url(SPREADSHEET_URL).sheet1

def save_movie_to_sheet(code: str, file_id: str):
    # Google Sheets jadvalining oxiriga code va file_id ni qo'shadi
    sheet.append_row([code, file_id])

def get_movie_from_sheet(code: str):
    # Google Sheets jadvalidan kodni qidirib, uning file_id sini topadi
    records = sheet.get_all_records()
    for row in records:
        if str(row.get("code")) == str(code):
            return row.get("file_id")
    return None


# --- 1. BARCHA KANALGA OBUNANI TEKSHIRISH ---
async def check_subscription(user_id: int) -> bool:
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel["username"], user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                return False
        except TelegramBadRequest:
            return False
    return True


# --- 2. OBUNA UCHUN TUGMALAR ---
def get_subscription_keyboard():
    builder = InlineKeyboardBuilder()
    for i, channel in enumerate(CHANNELS, start=1):
        builder.row(types.InlineKeyboardButton(text=f"➕ {i}-kanalga obuna bo'lish", url=channel["url"]))
    builder.row(types.InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
    builder.row(types.InlineKeyboardButton(text="💎 Premium", callback_data="premium"))
    return builder.as_markup()


# --- 3. START VA CALLBACKLAR ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    is_subscribed = await check_subscription(user_id)
    
    if not is_subscribed:
        await message.answer(
            "📢 Botdan to'liq foydalanish uchun quyidagi barcha 3 ta kanalga obuna bo'ling:",
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
            "Rahmat! Barcha kanallarga obuna tasdiqlandi ✅\n\n🎬 Endi kino kodini yuborishingiz mumkin:"
        )
    else:
        await callback.answer("❌ Siz hali hamma kanalga obuna bo'lmadingiz!", show_alert=True)

@dp.callback_query(lambda c: c.data == "premium")
async def process_premium(callback: types.CallbackQuery):
    await callback.answer("💎 Premium tez orada ishga tushadi!", show_alert=True)


# --- 4. XABARLAR VA KINO QIDIRISH (GOOGLE SHEETS BILAN) ---
@dp.message()
async def message_handler(message: types.Message):
    user_id = message.from_user.id
    
    # Agar siz (admin) videoni kod (caption) bilan botga yuborsangiz, u Google Sheets jadvaliga saqlanadi
    if message.video and message.caption:
        code = message.caption.strip()
        file_id = message.video.file_id
        save_movie_to_sheet(code, file_id)
        await message.answer(f"✅ Kino Google Sheets jadvaliga muvaffaqiyatli saqlandi! Kodi: {code}")
        return

    # Obunani tekshirish
    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        await message.answer(
            "📢 Botdan foydalanish uchun avval quyidagi barcha kanallarga obuna bo'ling:",
            reply_markup=get_subscription_keyboard()
        )
        return
    
    # Matn (kino kodi) kelganini tekshirish
    if not message.text:
        await message.answer("❌ Iltimos, kino kodini raqam ko'rinishida yuboring (masalan: 1):")
        return
    
    code = message.text.strip()
    file_id = get_movie_from_sheet(code)
    
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
            "❌ Kechirasiz, bu kod bo'yicha Google Sheets jadvalidan hech qanday kino topilmadi."
        )


# --- 5. BOTNI ISHGA TUSHIRISH ---
import asyncio

async def main():
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())  