import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Telegram Bot Token va Render sayt havolasi
TOKEN = "8995342958:AAEYriJLB4BvroCOF7qLBsptPqFeyT8dWDg"
WEB_APP_URL = "https://qalampir-miner-huy8.onrender.com"

logging.basicConfig(level=logging.INFO)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name

    # Mini App va Kanal tugmalari
    keyboard = [
        [
            InlineKeyboardButton(
                "🌶️ Qalampir Miner-ni O'ynash",
                web_app={"url": WEB_APP_URL},
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Salom, {user_name}! 🌶️\n\n"
        f"**Qalampir Miner** ekosistemasiga xush kelibsiz!\n\n"
        f"🎮 O'yin ichida sizni:\n"
        f"• Battle Pass (Mavsumiy darajalar)\n"
        f"• Lootbox va Noyob Artefaktlar\n"
        f"• Auto-Miner va Passiv daromad\n"
        f"• Haptic Vibratsiya effekti kutmoqda!\n\n"
        f"O'yinni boshlash uchun pastdagi tugmani bosing:",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()
