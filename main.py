import os
import asyncio
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لینک ویدیو را ارسال کنید تا دانلود کنم.")

def download_via_cobalt(url, output_path):
    # استفاده از ساختار جدید API Cobalt
    api_url = "https://api.cobalt.tools/"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }
    payload = {
        "url": url,
        "videoQuality": "720"
    }
    
    response = requests.post(api_url, json=payload, headers=headers, timeout=15)
    
    if response.status_code != 200:
        raise Exception(f"خطای سرویس API (کد {response.status_code})")
        
    data = response.json()
    
    # دریافت لینک مستقیم بر اساس وضعیت پاسخ Cobalt
    download_url = None
    if data.get("status") in ["tunnel", "redirect"]:
        download_url = data.get("url")
    elif data.get("status") == "picker":
        # اگر چند کیفیت وجود داشت، اولی را انتخاب کن
        download_url = data.get("picker", [{}])[0].get("url")
        
    if not download_url:
        error_code = data.get("text", "پاسخ نامعتبر از API")
        raise Exception(f"خطای Cobalt: {error_code}")
        
    # دانلود فایل با جریان داده (Streaming)
    with requests.get(download_url, stream=True, headers={"User-Agent": headers["User-Agent"]}) as r:
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return True

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("لطفاً یک لینک معتبر بفرستید.")
        return

    msg = await update.message.reply_text("⏳ در حال پردازش و دانلود ویدیو...")
    file_path = f"/tmp/{update.message.message_id}.mp4"
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_via_cobalt, url, file_path)

        await msg.edit_text("📤 در حال آپلود به تلگرام...")
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption="بفرمایید! ویدیو دانلود شد.")
        
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f"❌ خطایی در دانلود رخ داد: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

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
