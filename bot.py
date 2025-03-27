import os
import asyncio
import requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext
import yt_dlp
import ffmpeg
from PIL import Image, ImageDraw, ImageFont
from config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING

# Telethon बॉट और असिस्टेंट क्लाइंट सेटअप
bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
assistant = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

music_queue = []  # Queue सिस्टम

# ऑडियो डाउनलोड और प्रोसेसिंग फ़ंक्शन
async def download_audio(song_name):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}],
        'outtmpl': 'song.mp3'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{song_name}", download=True)
        return "song.mp3", info['entries'][0]['thumbnail'], info['entries'][0]['title']

# वॉयस चैट में स्ट्रीमिंग फ़ंक्शन
async def stream_audio(chat_id, audio_file):
    await assistant.join_call(chat_id)
    process = (
        ffmpeg
        .input(audio_file)
        .output("pipe:", format="opus", acodec="libopus", audio_bitrate="128k")
        .run_async(pipe_stdout=True, pipe_stderr=True)
    )
    
    async for chunk in process.stdout:
        await assistant.send_file(chat_id, chunk)

# कस्टम थंबनेल बनाना
def create_thumbnail(song_title, thumbnail_url):
    base_image = Image.open("template.jpg").convert("RGBA")
    song_thumb = Image.open(requests.get(thumbnail_url, stream=True).raw).convert("RGBA")

    song_thumb = song_thumb.resize((300, 300))
    base_image.paste(song_thumb, (50, 50), song_thumb)

    draw = ImageDraw.Draw(base_image)
    font = ImageFont.truetype("arial.ttf", 30)
    draw.text((400, 100), song_title, fill="white", font=font)

    final_thumb = "final_thumb.png"
    base_image.save(final_thumb)
    return final_thumb

# Telegram Bot Command Handlers
async def start(update: Update, context: CallbackContext) -> None:
    buttons = [[InlineKeyboardButton("Join Support", url="https://t.me/your_support_group")]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("I am a Streaming Bot! Use /play <song name> to stream.", reply_markup=reply_markup)

async def play(update: Update, context: CallbackContext) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Usage: /play <song name>")
        return
    
    song_name = " ".join(context.args)
    chat_id = update.message.chat_id
    user_name = update.message.from_user.first_name

    await update.message.reply_text(f"🔎 Searching for '{song_name}' on YouTube...")
    
    audio_file, thumbnail_url, song_title = await download_audio(song_name)

    if len(music_queue) == 0:
        music_queue.append((audio_file, chat_id, song_title, user_name))
        
        thumb_file = create_thumbnail(song_title, thumbnail_url)
        await update.message.reply_photo(photo=open(thumb_file, "rb"), caption=f"🎵 Now Playing: {song_title}\nRequested by: {user_name}")

        await stream_audio(chat_id, audio_file)
    else:
        music_queue.append((audio_file, chat_id, song_title, user_name))
        await update.message.reply_text(f"🎵 Added 1 music: {song_title}\nRequested by: {user_name}")

async def skip(update: Update, context: CallbackContext) -> None:
    if len(music_queue) > 1:
        music_queue.pop(0)
        next_song = music_queue[0]
        
        thumb_file = create_thumbnail(next_song[2], next_song[3])
        await update.message.reply_photo(photo=open(thumb_file, "rb"), caption=f"🎵 Now Playing: {next_song[2]}\nRequested by: {next_song[3]}")
        
        await stream_audio(next_song[1], next_song[0])
    else:
        await update.message.reply_text("🎵 No more songs in the queue!")

# बॉट स्टार्ट करें
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("play", play))
    dp.add_handler(CommandHandler("skip", skip))

    updater.start_polling()
    updater.idle()

# Telethon क्लाइंट रन करें
async def run_bot():
    await assistant.start()
    await bot.run_until_disconnected()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    main()
