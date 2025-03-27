import os
import asyncio
import requests
from pyrogram import Client, filters
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp
import ffmpeg
from PIL import Image, ImageDraw, ImageFont
from config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING

# Pyrogram Bot और Assistant Client सेटअप
bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
vc = PyTgCalls(assistant)  # Voice Chat के लिए PyTgCalls

music_queue = []  # Queue सिस्टम

# YouTube से ऑडियो डाउनलोड करने का फ़ंक्शन
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
    await vc.join_group_call(chat_id, AudioPiped(audio_file, StreamType().pulse_stream))
    print(f"🎶 Playing: {audio_file}")

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

# /start Command
@bot.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text("I am a Streaming Bot! Use /play <song name> to stream.")

# /play Command
@bot.on_message(filters.command("play"))
async def play(_, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /play <song name>")
        return
    
    song_name = " ".join(message.command[1:])
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    await message.reply_text(f"🔎 Searching for '{song_name}' on YouTube...")
    
    audio_file, thumbnail_url, song_title = await download_audio(song_name)

    if len(music_queue) == 0:
        music_queue.append((audio_file, chat_id, song_title, user_name))
        
        thumb_file = create_thumbnail(song_title, thumbnail_url)
        await message.reply_photo(photo=open(thumb_file, "rb"), caption=f"🎵 Now Playing: {song_title}\nRequested by: {user_name}")

        await stream_audio(chat_id, audio_file)
    else:
        music_queue.append((audio_file, chat_id, song_title, user_name))
        await message.reply_text(f"🎵 Added 1 music: {song_title}\nRequested by: {user_name}")

# /skip Command
@bot.on_message(filters.command("skip"))
async def skip(_, message):
    if len(music_queue) > 1:
        music_queue.pop(0)
        next_song = music_queue[0]
        
        thumb_file = create_thumbnail(next_song[2], next_song[3])
        await message.reply_photo(photo=open(thumb_file, "rb"), caption=f"🎵 Now Playing: {next_song[2]}\nRequested by: {next_song[3]}")
        
        await stream_audio(next_song[1], next_song[0])
    else:
        await message.reply_text("🎵 No more songs in the queue!")

# बॉट स्टार्ट करें
async def main():
    await bot.start()
    await assistant.start()
    await vc.start()
    print("🤖 Bot is running...")
    await idle()

if __name__ == "__main__":
    asyncio.run(main())
