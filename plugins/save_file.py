import logging
import os
import time
import re
import requests
from urllib.parse import quote, unquote
from chat import Chat
from config import Config
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from helper_func.progress_bar import progress_bar
from helper_func.dbhelper import Database as Db

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)
logging.getLogger("pyrogram").setLevel(logging.WARNING)

db = Db()

async def _check_user(filt, c, m):
    return str(m.from_user.id) in Config.ALLOWED_USERS

check_user = filters.create(_check_user)

def get_mux_buttons():
    """Returns InlineKeyboardMarkup for muxing options."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Softmux", callback_data="softmux"),
         InlineKeyboardButton("Hardmux", callback_data="hardmux")]
    ])

@Client.on_message(filters.document & check_user & filters.private)
async def save_doc(client, message):
    chat_id = message.from_user.id
    start_time = time.time()
    downloading = await client.send_message(chat_id, "Downloading your File!")

    download_location = await client.download_media(
        message=message,
        file_name=os.path.join(Config.DOWNLOAD_DIR, ""),
        progress=progress_bar,
        progress_args=("Initializing", downloading, start_time),
    )

    if not download_location:
        return await downloading.edit_text("Downloading Failed!")

    await downloading.edit_text(Chat.DOWNLOAD_SUCCESS.format(round(time.time() - start_time)))

    tg_filename = os.path.basename(download_location)
    og_filename = message.document.file_name if message.document.file_name else tg_filename
    ext = og_filename.split(".")[-1]
    filename = f"{round(start_time)}.{ext}"

    os.rename(os.path.join(Config.DOWNLOAD_DIR, tg_filename), os.path.join(Config.DOWNLOAD_DIR, filename))

    if ext in ["srt", "ass"]:
        db.put_sub(chat_id, filename)
        text = "Subtitle file downloaded successfully."
        reply_markup = get_mux_buttons() if db.check_video(chat_id) else None
    elif ext in ["mp4", "mkv"]:
        db.put_video(chat_id, filename, og_filename)
        text = "Video file downloaded successfully."
        reply_markup = get_mux_buttons() if db.check_sub(chat_id) else None
    else:
        text = Chat.UNSUPPORTED_FORMAT.format(ext) + f"\nFile = {tg_filename}"
        os.remove(os.path.join(Config.DOWNLOAD_DIR, tg_filename))
        reply_markup = None

    await downloading.edit_text(text, reply_markup=reply_markup)

@Client.on_message(filters.video & check_user & filters.private)
async def save_video(client, message):
    chat_id = message.from_user.id
    start_time = time.time()
    downloading = await client.send_message(chat_id, "Downloading your File!")

    download_location = await client.download_media(
        message=message,
        file_name=os.path.join(Config.DOWNLOAD_DIR, ""),
        progress=progress_bar,
        progress_args=("Initializing", downloading, start_time),
    )

    if not download_location:
        return await downloading.edit_text("Downloading Failed!")

    await downloading.edit_text(Chat.DOWNLOAD_SUCCESS.format(round(time.time() - start_time)))

    tg_filename = os.path.basename(download_location)
    og_filename = message.video.file_name if message.video else tg_filename
    ext = og_filename.split(".")[-1]
    filename = f"{round(start_time)}.{ext}"

    os.rename(os.path.join(Config.DOWNLOAD_DIR, tg_filename), os.path.join(Config.DOWNLOAD_DIR, filename))

    db.put_video(chat_id, filename, og_filename)
    text = "Video file downloaded successfully."
    reply_markup = get_mux_buttons() if db.check_sub(chat_id) else None

    await downloading.edit_text(text, reply_markup=reply_markup)

@Client.on_message(filters.text & filters.regex(r"^https?://") & check_user)
async def save_url(client, message):
    chat_id = message.from_user.id
    url = message.text.split("|")[0].strip()
    save_filename = message.text.split("|")[1].strip() if "|" in message.text and len(message.text.split("|")) == 2 else None

    if save_filename and len(save_filename) > 60:
        return await client.send_message(chat_id, Chat.LONG_CUS_FILENAME)

    r = requests.get(url, stream=True, allow_redirects=True)

    if save_filename is None:
        if "content-disposition" in r.headers:
            res = re.search(r'filename="(.*?)"', r.headers["content-disposition"])
            save_filename = res.group(1) if res else unquote(url.split("?")[0].split("/")[-1])
        else:
            save_filename = unquote(url.split("?")[0].split("/")[-1])

    sent_msg = await client.send_message(chat_id, "Preparing Your Download")
    ext = save_filename.split(".")[-1]

    if ext not in ["mp4", "mkv"]:
        return await sent_msg.edit_text(Chat.UNSUPPORTED_FORMAT.format(ext))

    size = int(r.headers.get("content-length", 0))

    if not size:
        return await sent_msg.edit_text(Chat.FILE_SIZE_ERROR)
    if size > 2 * 1000 * 1000 * 1000:  # 2GB Limit
        return await sent_msg.edit_text(Chat.MAX_FILE_SIZE)

    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)

    current = 0
    start = time.time()
    filename = f"{round(start)}.{ext}"
    file_path = os.path.join(Config.DOWNLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            if chunk:
                written = f.write(chunk)
                current += written
                await progress_bar(current, size, "Downloading Your File!", sent_msg, start)

    try:
        await sent_msg.edit_text(Chat.DOWNLOAD_SUCCESS.format(round(time.time() - start)))
    except:
        pass

    db.put_video(chat_id, filename, save_filename)
    text = "Video file downloaded successfully."
    reply_markup = get_mux_buttons() if db.check_sub(chat_id) else None

    try:
        await sent_msg.edit_text(text, reply_markup=reply_markup)
    except:
        pass
