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

def extract_video_id(url):
    """استخراج Video ID از لینک یوتیوب"""
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "watch?v=" in url:
        return url.split("watch?v=")[1].split("&")[0]
    elif "shorts/" in url:
        return url.split("shorts/")[1].split("?")[0]
    return None

def download_via_invidious(url, output_path):
    video_id = extract_video_id(url)
    if not video_id:
        raise Exception("لینک یوتیوب نامعتبر است.")

    # اینستنس‌های فعال و معتبر Invidious API
    instances = [
        "https://inv.riverside.rocks",
        "https://invidious.nerdvpn.de",
        "https://invidious.drgns.space",
        "https://vid.puffyan.us"
    ]

    download_url = None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    # دریافت اطلاعات ویدیو از API اینستنس‌ها
    for instance in instances:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, headers=headers, timeout=8)
            if res.status_code == 200:
                data = res.json()
                format_streams = data.get("formatStreams", [])
                
                # پیدا کردن بهترین کیفیت MP4 ترکیبی (صدا + تصویر)
                for stream in reversed(format_streams):
                    if stream.get("container") == "mp4" and stream.get("url"):
                        download_url = stream.get("url")
                        break
                if download_url:
                    break
        except Exception:
            continue

    if not download_url:
        raise Exception("امکان استخراج لینک دانلود مستقیم وجود نداشت.")

    # دانلود فایل mp4 با Streaming
    with requests.get(download_url, stream=True, headers=headers, timeout=30) as r:
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
        await loop.run_in_executor(None, download_via_invidious, url, file_path)

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
