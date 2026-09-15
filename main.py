import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from pytubefix import YouTube

TOKEN = os.environ.get("BOT_TOKEN")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لینک ویدیو یوتیوب را بفرستید تا دانلود کنم.")

def fetch_and_download(url, file_path):
    # استفاده از کلاینت ANDROID_VR که بیشترین سرعت و بدون گیری دانلود را دارد
    yt = YouTube(url, client='ANDROID_VR')
    ys = yt.streams.filter(progressive=True, file_extension='mp4').get_highest_resolution()
    
    if not ys:
        ys = yt.streams.get_highest_resolution()
        
    ys.download(output_path="/tmp", filename=os.path.basename(file_path))
    return yt.title

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not ("youtube.com" in url or "youtu.be" in url):
        await update.message.reply_text("لطفاً یک لینک معتبر از یوتیوب بفرستید.")
        return

    msg = await update.message.reply_text("⏳ در حال دانلود ویدیو از یوتیوب...")
    file_path = f"/tmp/{update.message.message_id}.mp4"
    
    try:
        loop = asyncio.get_event_loop()
        # اجرای دانلود در Thread جداگانه تا ربات گیر نکند
        title = await loop.run_in_executor(None, fetch_and_download, url, file_path)

        await msg.edit_text("📤 در حال آپلود به تلگرام...")
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption=f"🎥 {title}")
        
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
