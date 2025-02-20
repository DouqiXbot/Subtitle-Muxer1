import logging
import os
import time
import re
import requests
from urllib.parse import unquote
from pathlib import Path
from pyrogram import Client, filters
from config import Config
from helper_func.progress_bar import progress_bar
from helper_func.dbhelper import Database as Db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Initialize database
db = Db()

# Custom filter to check if the user is allowed
async def _check_user(_, __, m):
    return str(m.from_user.id) in Config.ALLOWED_USERS

check_user = filters.create(_check_user)

class Chat:
    DOWNLOAD_SUCCESS = "✅ File downloaded successfully in {} seconds!"
    UNSUPPORTED_FORMAT = "❌ Unsupported file format: `{}`"
    FILE_SIZE_ERROR = "❌ Couldn't determine the file size."
    MAX_FILE_SIZE = "❌ File size exceeds the 2GB limit."
    LONG_CUS_FILENAME = "❌ Filename too long! Keep it under 60 characters."

async def safe_edit_message(message, new_text):
    """Safe edit function to avoid duplicate messages."""
    try:
        if message.text != new_text:  # ✅ Check for duplicate message
            await message.edit_text(new_text)
    except Exception as e:
        logger.warning(f"Edit message failed: {e}")

async def save_document_or_video(client, message, is_video=False):
    """Handles both document and video files."""
    chat_id = message.from_user.id
    start_time = time.time()
    downloading = await client.send_message(chat_id, "📥 Downloading your File...")

    download_location = await client.download_media(
        message=message,
        file_name=os.path.join(Config.DOWNLOAD_DIR, ""),
        progress=progress_bar,
        progress_args=("Initializing", downloading, start_time),
    )

    if not download_location:
        return await safe_edit_message(downloading, "❌ Downloading Failed!")

    await safe_edit_message(downloading, Chat.DOWNLOAD_SUCCESS.format(round(time.time() - start_time)))

    tg_filename = os.path.basename(download_location)
    og_filename = message.video.file_name if is_video else message.document.file_name
    og_filename = og_filename if og_filename else tg_filename

    ext = og_filename.split(".")[-1].lower()
    filename = f"{round(start_time)}.{ext}"

    os.rename(os.path.join(Config.DOWNLOAD_DIR, tg_filename), os.path.join(Config.DOWNLOAD_DIR, filename))

    if ext in ["srt", "ass"]:
        db.put_sub(chat_id, filename)
        new_text = (
            "✅ Subtitle file downloaded successfully.\n"
            "Choose your desired muxing!\n[ /softmux , /hardmux ]"
            if db.check_video(chat_id) else "✅ Subtitle file downloaded.\nNow send a Video File!"
        )
    elif ext in ["mp4", "mkv"]:
        db.put_video(chat_id, filename, og_filename)
        new_text = (
            "✅ Video file downloaded successfully.\n"
            "Choose your desired muxing.\n[ /softmux , /hardmux ]"
            if db.check_sub(chat_id) else "✅ Video file downloaded successfully.\nNow send a Subtitle file!"
        )
    else:
        new_text = Chat.UNSUPPORTED_FORMAT.format(ext) + f"\nFile = {tg_filename}"
        os.remove(os.path.join(Config.DOWNLOAD_DIR, tg_filename))

    await safe_edit_message(downloading, new_text)

@Client.on_message(filters.document & check_user & filters.private)
async def save_doc(client, message):
    """Handle document uploads (subtitles or videos)."""
    await save_document_or_video(client, message)

@Client.on_message(filters.video & check_user & filters.private)
async def save_video(client, message):
    """Handle video uploads."""
    await save_document_or_video(client, message, is_video=True)

@Client.on_message(filters.text & filters.regex(r"^https?://") & check_user)
async def save_url(client, message):
    """Save a video file from a URL."""
    chat_id = message.from_user.id
    url = message.text.split("|")[0].strip()
    save_filename = message.text.split("|")[1].strip() if "|" in message.text and len(message.text.split("|")) == 2 else None

    if save_filename and len(save_filename) > 60:
        await client.send_message(chat_id, Chat.LONG_CUS_FILENAME)
        return

    try:
        sent_msg = await client.send_message(chat_id, "📥 Preparing Your Download...")
        r = requests.get(url, stream=True, allow_redirects=True, timeout=30)

        if r.status_code != 200:
            await sent_msg.edit_text("❌ Invalid URL or server error.")
            return

        if "content-disposition" in r.headers:
            res = re.search(r'filename="(.*?)"', r.headers["content-disposition"])
            save_filename = res.group(1) if res else unquote(url.split("?")[0].split("/")[-1])
        else:
            save_filename = unquote(url.split("?")[0].split("/")[-1])

        ext = save_filename.split(".")[-1].lower()
        if ext not in ["mp4", "mkv"]:
            await sent_msg.edit_text(Chat.UNSUPPORTED_FORMAT.format(ext))
            return

        size = int(r.headers.get("content-length", 0))
        if not size:
            await sent_msg.edit_text(Chat.FILE_SIZE_ERROR)
            return
        if size > 2 * 1000 * 1000 * 1000:  # 2GB Limit
            await sent_msg.edit_text(Chat.MAX_FILE_SIZE)
            return

        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        timestamp = str(int(time.time()))
        counter = 0
        base_filename = f"{timestamp}_{counter}.{ext}"
        file_path = Path(Config.DOWNLOAD_DIR) / base_filename

        while file_path.exists():
            counter += 1
            base_filename = f"{timestamp}_{counter}.{ext}"
            file_path = Path(Config.DOWNLOAD_DIR) / base_filename

        current = 0
        start = time.time()
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    written = f.write(chunk)
                    current += written
                    await progress_bar(current, size, "Downloading Your File!", sent_msg, start)

        await sent_msg.edit_text(Chat.DOWNLOAD_SUCCESS.format(round(time.time() - start)))

        db.put_video(chat_id, str(file_path.name), save_filename)
        response = (
            "✅ Video File Downloaded.\n"
            "Choose your desired muxing!\n[ /softmux , /hardmux ]"
            if db.check_sub(chat_id) else
            "✅ Video File Downloaded.\nNow send a Subtitle file!"
        )
        await sent_msg.edit_text(response)

    except requests.RequestException as e:
        logger.error(f"URL download error: {e}")
        await sent_msg.edit_text(f"❌ Download failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in URL download: {e}")
        await sent_msg.edit_text(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    Client("muxbot").run()
