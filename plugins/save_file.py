import logging
import os
import time
import re
import requests
from urllib.parse import quote, unquote
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
    """Static class for chat messages."""
    DOWNLOAD_SUCCESS = "✅ Download completed in {} seconds!"
    UNSUPPORTED_FORMAT = "❌ Unsupported format: {}. Only mp4, mkv, srt, ass are supported."
    FILE_SIZE_ERROR = "❌ Cannot determine file size. Please try a different URL."
    MAX_FILE_SIZE = "❌ File size exceeds 2GB limit."
    LONG_CUS_FILENAME = "❌ Custom filename too long (max 60 characters)."

async def save_document_or_video(client, message, is_video: bool = False):
    """Save a document or video file from Telegram."""
    chat_id = message.from_user.id
    start_time = time.time()
    downloading = await client.send_message(chat_id, "📥 Downloading your File...")

    try:
        media = message.document if not is_video else message.video
        download_location = await client.download_media(
            message=message,
            file_name=str(Path(Config.DOWNLOAD_DIR) / ""),
            progress=progress_bar,
            progress_args=("Downloading", downloading, start_time),
        )

        if not download_location:
            await downloading.edit_text("❌ Downloading Failed!")
            return

        await downloading.edit_text(Chat.DOWNLOAD_SUCCESS.format(round(time.time() - start_time)))

        # Get file details
        tg_filename = Path(download_location).name
        og_filename = media.file_name if media.file_name else tg_filename
        ext = og_filename.split(".")[-1].lower()

        # Ensure unique filename using timestamp and counter
        timestamp = str(int(time.time()))
        counter = 0
        base_filename = f"{timestamp}_{counter}.{ext}"
        file_path = Path(Config.DOWNLOAD_DIR) / base_filename

        while file_path.exists():
            counter += 1
            base_filename = f"{timestamp}_{counter}.{ext}"
            file_path = Path(Config.DOWNLOAD_DIR) / base_filename

        # Rename the downloaded file
        os.rename(download_location, file_path)

        # Store in database
        if ext in ["srt", "ass"]:
            db.put_sub(chat_id, str(file_path.name))
            new_message = (
                "✅ Subtitle file downloaded successfully.\n"
                "Choose your desired muxing!\n[ /softmux , /hardmux ]"
                if db.check_video(chat_id) else
                "✅ Subtitle file downloaded.\nNow send a Video File!"
            )

            # ✅ Prevent Duplicate Messages
            if "Subtitle file downloaded successfully" not in downloading.text:
                await downloading.edit_text(new_message)

        elif ext in ["mp4", "mkv"]:
            db.put_video(chat_id, str(file_path.name), og_filename)
            new_message = (
                "✅ Video file downloaded successfully.\n"
                "Choose your desired muxing!\n[ /softmux , /hardmux ]"
                if db.check_sub(chat_id) else
                "✅ Video file downloaded successfully.\nNow send a Subtitle file!"
            )
            await downloading.edit_text(new_message)

        else:
            response = Chat.UNSUPPORTED_FORMAT.format(ext)
            file_path.unlink()
            await downloading.edit_text(response)
            return

    except Exception as e:
        logger.error(f"Error saving {('video' if is_video else 'document')}: {e}")
        await downloading.edit_text(f"❌ Error saving file: {str(e)}")
@Client.on_message(filters.document & check_user & filters.private)
async def save_doc(client, message):
    """Handle document uploads (subtitles or videos)."""
    await save_document_or_video(client, message)

@Client.on_message(filters.video & check_user & filters.private)
async def save_video(client, message):
    """Handle video uploads."""
    await save_document_or_video(client, message, is_video=True)

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
