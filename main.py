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
    # استفاده از API عمومی Cobalt برای دریافت لینک مستقیم ویدیو
    api_url = "https://api.cobalt.tools/api/json"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "vCodec": "h264"
    }
    
    response = requests.post(api_url, json=payload, headers=headers)
    data = response.json()
    
    if "url" in data:
        video_url = data["url"]
        # دانلود فایل ویدیو از لینک مستقیم
        with requests.get(video_url, stream=True) as r:
            r.raise_for_status()
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    else:
        raise Exception("امکان دریافت لینک دانلود وجود نداشت.")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("لطفاً یک لینک معتبر بفرستید.")
        return

    msg = await update.message.reply_text("⏳ در حال دانلود ویدیو...")
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
