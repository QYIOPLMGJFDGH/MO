import os
import asyncio
import requests
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, StreamAudioEnded
import yt_dlp
import ffmpeg
from PIL import Image, ImageDraw, ImageFont
from config import API_ID, API_HASH, BOT_TOKEN, SESSION_STRING

# Initialize Pyrogram Client & PyTgCalls
app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
pytgcalls = PyTgCalls(assistant)

music_queue = {}  # Dictionary for Queue System

# Function to Download Audio from YouTube
async def download_audio(song_name):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "song.mp3",
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "opus", "preferredquality": "128"}],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{song_name}", download=True)
        return "song.mp3", info["entries"][0]["thumbnail"], info["entries"][0]["title"]

# Function to Generate Custom Thumbnail
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

# Function to Play Audio in VC
async def stream_audio(chat_id, audio_file):
    await pytgcalls.join_group_call(chat_id, AudioPiped(audio_file))

# Play Command
@app.on_message(filters.command("play") & filters.group)
async def play(client, message):
    chat_id = message.chat.id
    user_name = message.from_user.first_name

    if len(message.command) < 2:
        await message.reply_text("Usage: `/play <song name>`")
        return

    song_name = " ".join(message.command[1:])
    await message.reply_text(f"🔎 Searching for '{song_name}' on YouTube...")

    audio_file, thumbnail_url, song_title = await download_audio(song_name)

    if chat_id not in music_queue:
        music_queue[chat_id] = []

    if not music_queue[chat_id]:
        music_queue[chat_id].append((audio_file, song_title, user_name))
        thumb_file = create_thumbnail(song_title, thumbnail_url)
        await message.reply_photo(photo=open(thumb_file, "rb"), caption=f"🎵 **Now Playing:** {song_title}\n🔹 **Requested by:** {user_name}")
        await stream_audio(chat_id, audio_file)
    else:
        music_queue[chat_id].append((audio_file, song_title, user_name))
        await message.reply_text(f"🎵 **Added to Queue:** {song_title}\n🔹 **Requested by:** {user_name}")

# Skip Command
@app.on_message(filters.command("skip") & filters.group)
async def skip(client, message):
    chat_id = message.chat.id
    if chat_id in music_queue and len(music_queue[chat_id]) > 1:
        music_queue[chat_id].pop(0)
        next_song = music_queue[chat_id][0]
        
        thumb_file = create_thumbnail(next_song[1], "default_thumb.jpg")
        await message.reply_photo(photo=open(thumb_file, "rb"), caption=f"🎵 **Now Playing:** {next_song[1]}\n🔹 **Requested by:** {next_song[2]}")
        await stream_audio(chat_id, next_song[0])
    else:
        await message.reply_text("🎵 No more songs in the queue!")

# Stop Command
@app.on_message(filters.command("stop") & filters.group)
async def stop(client, message):
    chat_id = message.chat.id
    if chat_id in music_queue:
        music_queue.pop(chat_id)
    await pytgcalls.leave_group_call(chat_id)
    await message.reply_text("🛑 Stopped Music & Left VC.")

# Handle Auto-Skip When Song Ends
@pytgcalls.on_stream_end()
async def on_stream_end(_, update: StreamAudioEnded):
    chat_id = update.chat_id
    if chat_id in music_queue and len(music_queue[chat_id]) > 1:
        music_queue[chat_id].pop(0)
        next_song = music_queue[chat_id][0]
        await stream_audio(chat_id, next_song[0])
    else:
        await pytgcalls.leave_group_call(chat_id)

# Bot Start
async def main():
    await app.start()
    await assistant.start()
    await pytgcalls.start()
    print("🚀 Bot is Running...")
    await asyncio.get_event_loop().run_forever()

if __name__ == "__main__":
    asyncio.run(main())
