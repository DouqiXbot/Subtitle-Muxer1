from pyrogram import Client, filters
import os
import subprocess

app = Client("subtitle_bot")

# Dictionary to track users waiting for a video file
waiting_for_video = {}

# Command: /extract
@app.on_message(filters.command("extract"))
async def extract_subtitle_command(client, message):
    user_id = message.from_user.id
    waiting_for_video[user_id] = True  # Mark user as waiting for a file
    await message.reply_text("📂 Please send me a video file, and I'll extract the subtitles.")

# Handle video file upload
@app.on_message(filters.video | filters.document)
async def handle_video(client, message):
    user_id = message.from_user.id
    if user_id not in waiting_for_video or not waiting_for_video[user_id]:
        await message.reply_text("❌ Please use /extract first before sending a video file.")
        return

    # Download video
    video_path = await message.download()
    subtitle_path = video_path.rsplit(".", 1)[0] + ".srt"  # Save subtitle as .srt

    # Extract subtitles using ffmpeg
    extract_command = f'ffmpeg -i "{video_path}" -map 0:s:0 "{subtitle_path}"'
    process = subprocess.run(extract_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if process.returncode == 0:
        await message.reply_document(subtitle_path, caption="✅ Subtitle extracted successfully!")
        os.remove(subtitle_path)  # Cleanup
    else:
        await message.reply_text("❌ No subtitles found in the video.")

    os.remove(video_path)  # Cleanup
    waiting_for_video.pop(user_id, None)  # Remove from waiting list

app.run()
