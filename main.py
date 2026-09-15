import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# دریافت توکن از متغیرهای محیطی Render
TOKEN = os.environ.get("BOT_TOKEN")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لینک فیلم یا ویدیو رو برام بفرست تا برات دانلود کنم.")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("لطفا یک لینک معتبر بفرستید.")
        return

    msg = await update.message.reply_text("⏳ در حال دانلود ویدیو... لطفا صبور باشید.")
    output_path = f"/tmp/{update.message.message_id}.mp4"

    # تنظیمات پیشرفته با پشتیبانی از پروکسی و کلاینت‌های غیردیتاسنتری
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        # استفاده از کلاینت‌های تی‌وی که حساسیتی روی آی‌پی ندارند
        'extractor_args': {
            'youtube': {
                'player_client': ['tv', 'mweb', 'android'],
            }
        },
        # در صورت نیاز می‌توانید یک پروکسی سالم (HTTP/SOCKS5) قرار دهید
        # 'proxy': 'http://USERNAME:PASSWORD@HOST:PORT',
    }

    # اگر فایل کوکی محرمانه در Render تعریف شده باشد
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = "cookies.txt"

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))

        await msg.edit_text("📤 در حال آپلود ویدیو به تلگرام...")
        with open(output_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption="بفرمایید! ویدیو شما دانلود شد.")
        
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ خطایی در دانلود رخ داد: {str(e)}")
    finally:
        # پاک‌سازی حافظه موقت سرور
        if os.path.exists(output_path):
            os.remove(output_path)

application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

@app.route("/", methods=["POST"])
def webhook():
    if request.method == "POST":
        asyncio.run(application.initialize())
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))
        return "OK", 200
    return "Server is running!", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is active!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
