import logging
import os
import time
import re
import asyncio
from typing import Dict, Optional
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# Initialize database
db = Db()

# Custom filter to check if the user is allowed
async def _check_user(_, __, m) -> bool:
    return str(m.from_user.id) in Config.ALLOWED_USERS

check_user = filters.create(_check_user)

# Regex pattern to parse FFmpeg progress
PROGRESS_PATTERN = re.compile(r'(frame|fps|size|time|bitrate|speed)\s*=\s*(\S+)')

def parse_progress(line: str) -> Dict[str, str]:
    """Parse FFmpeg progress output into a dictionary."""
    return dict(PROGRESS_PATTERN.findall(line))

async def readlines(stream) -> bytes:
    """Asynchronously read lines from a stream."""
    pattern = re.compile(br'[\r\n]+')
    data = bytearray()
    while not stream.at_eof():
        lines = pattern.split(data)
        data[:] = lines.pop(-1)
        for line in lines:
            yield line
        data.extend(await stream.read(1024))

async def safe_edit_message(msg, text: str, retries: int = 1) -> None:
    """Safely edit a message with retry logic."""
    for attempt in range(retries + 1):
        try:
            await msg.edit(text)
            return
        except Exception as e:
            logger.warning(f"Edit failed: {e}")
            if "messages.EditMessage" in str(e) and attempt < retries:
                await asyncio.sleep(5)
            else:
                logger.error(f"Failed to edit message after {retries} retries: {e}")
                break

async def read_stderr(start: float, msg, process) -> str:
    """Read FFmpeg stderr and update progress."""
    error_log = []
    last_edit_time = time.time()
    async for line in readlines(process.stderr):
        line_str = line.decode('utf-8', errors='ignore')
        error_log.append(line_str)
        progress = parse_progress(line_str)
        if progress and (time.time() - last_edit_time >= 10):
            text = (
                "🔄 **Processing...**\n"
                f"Size: {progress.get('size', 'N/A')}\n"
                f"Time: {progress.get('time', 'N/A')}\n"
                f"Speed: {progress.get('speed', 'N/A')}"
            )
            await safe_edit_message(msg, text)
            last_edit_time = time.time()
    return "\n".join(error_log)

# Encoding options
ENCODING_OPTIONS = {
    "crf": ["18 (Quality)", "20 (Balanced)", "22 (Compression)"],
    "preset": ["medium", "fast", "veryfast", "ultrafast"],
    "codec": ["libx265", "libx264"],
    "font_size": ["18", "20", "24", "28"],
    "resolution": ["1280x720", "1920x1080", "Original"]
}

async def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate the encoding settings keyboard with default values if settings are missing."""
    default_settings = {
        "crf": "23",
        "preset": "ultrafast",
        "codec": "libx264",
        "font_size": "20",
        "resolution": "Original"
    }
    
    current_settings = db.get_encoding_settings(user_id) or {}
    logger.debug(f"Current settings for user {user_id}: {current_settings}")
    
    # Ensure all required keys are present
    current_settings = {**default_settings, **current_settings}
    
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"CRF: {current_settings['crf'].split()[0]}", callback_data="setting_crf")],
        [
            InlineKeyboardButton(f"Preset: {current_settings['preset']}", callback_data="setting_preset"),
            InlineKeyboardButton(f"Codec: {current_settings['codec']}", callback_data="setting_codec")
        ],
        [
            InlineKeyboardButton(f"Font: {current_settings['font_size']}pt", callback_data="setting_font_size"),
            InlineKeyboardButton(f"Res: {current_settings['resolution']}", callback_data="setting_resolution")
        ],
        [InlineKeyboardButton("🚀 Start Encoding", callback_data="burn")]
    ])

@Client.on_callback_query(filters.regex(r"^setting_(.+)$"))
async def encoding_settings_callback(client, query):
    """Handle settings selection callback."""
    setting_type = query.matches[0].group(1)
    user_id = query.from_user.id
    current_settings = db.get_encoding_settings(user_id) or {}
    current_value = current_settings.get(setting_type, "")

    buttons = [
        InlineKeyboardButton(
            f"{'✅ ' if option.startswith(current_value) else ''}{option}",
            callback_data=f"set_{setting_type}_{option.split()[0]}"
        ) for option in ENCODING_OPTIONS.get(setting_type, [])
    ]
    buttons.append(InlineKeyboardButton("🔙 Back", callback_data="settings_back"))

    await query.edit_message_text(
        f"Select {setting_type.replace('_', ' ').title()}:",
        reply_markup=InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    )

@Client.on_callback_query(filters.regex(r"^set_(.+)_(.+)$"))
async def set_encoding_parameter(client, query):
    """Set an encoding parameter and return to settings."""
    setting_type, value = query.matches[0].groups()
    user_id = query.from_user.id
    current_settings = db.get_encoding_settings(user_id) or {}
    current_settings[setting_type] = value
    db.set_encoding_settings(user_id, current_settings)

    await query.answer(f"{setting_type.title()} set to {value}!")
    await show_encoding_settings(client, query.message)

@Client.on_callback_query(filters.regex("settings_back"))
async def show_encoding_settings(client, query):
    """Show the main encoding settings menu."""
    user_id = query.from_user.id
    keyboard = await get_settings_keyboard(user_id)
    await query.edit_message_text("⚙️ Encoding Settings (Customize parameters):", reply_markup=keyboard)

@Client.on_message(filters.command('hardmux') & check_user & filters.private)
async def hardmux(client, message):
    """Handle the /hardmux command."""
    chat_id = message.from_user.id
    og_vid_filename = db.get_vid_filename(chat_id)
    og_sub_filename = db.get_sub_filename(chat_id)
    download_dir = Path(Config.DOWNLOAD_DIR)

    validation_errors = []
    if not og_vid_filename or not (download_dir / og_vid_filename).exists():
        validation_errors.append("First send a Video File")
    if not og_sub_filename or not (download_dir / og_sub_filename).exists():
        validation_errors.append("Send a Subtitle File!")

    if validation_errors:
        await client.send_message(chat_id, "\n".join(validation_errors))
        return

    keyboard = await get_settings_keyboard(chat_id)
    await message.reply_text("⚙️ Configure encoding parameters:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex("burn"))
async def start_encoding_process(client, query):
    """Start the video encoding process when the user presses 'Start Encoding'."""
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    download_dir = Path(Config.DOWNLOAD_DIR)

    logger.info(f"🔄 Starting encoding process for user {user_id}")

    # Retrieve required files and user settings
    og_vid_filename = db.get_vid_filename(chat_id)
    og_sub_filename = db.get_sub_filename(chat_id)
    user_settings = db.get_encoding_settings(user_id) or {}

    # Validate required files
    missing_files = []
    if not og_vid_filename or not (download_dir / og_vid_filename).exists():
        missing_files.append("❌ Video file is missing! Please upload it first.")
    if not og_sub_filename or not (download_dir / og_sub_filename).exists():
        missing_files.append("❌ Subtitle file is missing! Please upload it first.")

    if missing_files:
        await query.message.edit_text("\n".join(missing_files))
        logger.error(f"Encoding aborted due to missing files: {missing_files}")
        return

    # Ensure all required encoding settings are present
    default_settings = {
        "crf": "23",
        "preset": "ultrafast",
        "codec": "libx264",
        "font_size": "20",
        "resolution": "Original"
    }
    user_settings = {**default_settings, **user_settings}

    sent_msg = await query.message.edit_text("⚙️ Preparing encoding process...")

    try:
        hardmux_filename = await hardmux_vid(og_vid_filename, og_sub_filename, sent_msg, user_settings)
        if not hardmux_filename:
            await sent_msg.edit_text("❌ Encoding failed. Please check logs for details.")
            return

        final_filename = db.get_filename(chat_id) or f"{Path(og_vid_filename).stem}_hardmuxed.mp4"
        db.put_video(chat_id, og_vid_filename, final_filename)

        input_path = download_dir / hardmux_filename
        output_path = download_dir / final_filename
        os.rename(input_path, output_path)

        start_time = time.time()
        await client.send_document(
            chat_id,
            document=str(output_path),
            caption=f"✅ **Encoding Completed!**\n📄 Filename: `{final_filename}`",
            progress=progress_bar,
            progress_args=("Uploading your File!", sent_msg, start_time)
        )
        await sent_msg.edit_text(f"✅ **File Uploaded!**\n⏳ Time: `{round(time.time() - start_time)}s`")

    except Exception as e:
        logger.error(f"❌ Encoding or upload failed for user {user_id}: {e}")
        await sent_msg.edit_text(f"❌ An error occurred during encoding/upload:\n`{str(e)}`")

    # Cleanup files after processing
    cleanup_files = [og_sub_filename, og_vid_filename, final_filename]
    for file in cleanup_files:
        file_path = download_dir / file
        if file and file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"🧹 Deleted file: {file}")
            except OSError as e:
                logger.warning(f"⚠️ Failed to delete {file}: {e}")

    db.erase(chat_id)
    logger.info(f"✅ Encoding process completed for user {user_id}.")

async def hardmux_vid(vid_filename: str, sub_filename: str, msg, user_settings: Dict) -> Optional[str]:
    """Hardmux video with subtitles using FFmpeg."""
    start = time.time()
    download_dir = Path(Config.DOWNLOAD_DIR)
    vid = download_dir / vid_filename
    sub = download_dir / sub_filename
    output = f"{Path(vid_filename).stem}_hardmuxed.mp4"
    out_location = download_dir / output

    # Ensure font file exists
    font_path = Path.cwd() / "fonts" / "HelveticaRounded-Bold.ttf"
    if not font_path.exists():
        await safe_edit_message(msg, "❌ Font not found! Please add 'HelveticaRounded-Bold.ttf' in 'fonts' folder.")
        return None

    # Properly escape subtitle paths
    sub_path = sub.as_posix().replace(":", "\\:")
    formatted_sub = f"'{sub_path}'" if " " in sub.name else sub_path

    scale_filter = f"scale={user_settings['resolution']}," if user_settings["resolution"] != "Original" else ""

    command = [
        "ffmpeg", "-hide_banner", "-i", str(vid),
        "-vf", (
            f"{scale_filter}"
            f"subtitles={formatted_sub}:force_style="
            f"'FontName=HelveticaRounded-Bold,FontSize={user_settings['font_size']},"
            f"PrimaryColour={Config.FONT_COLOR},Outline={Config.BORDER_WIDTH}',"
            f"drawtext=text='{Config.WATERMARK}':fontfile='{font_path}':"
            "x=w-tw-10:y=10:fontsize=24:fontcolor=white:borderw=2:bordercolor=black"
        ),
        "-c:v", user_settings["codec"], "-preset", user_settings["preset"],
        "-crf", user_settings["crf"].split()[0], "-tag:v", "hvc1", "-c:a", "copy", "-y", str(out_location)
    ]

    logger.info(f"🚀 Running FFmpeg command: {' '.join(command)}")

    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    error_output = await read_stderr(start, msg, process)
    await process.wait()

    if process.returncode == 0:
        await safe_edit_message(msg, f"✅ Muxing Completed!\n⏳ Time: `{round(time.time() - start)}s`")
        return output
    else:
        trimmed_error = error_output[-3000:] if len(error_output) > 3000 else error_output
        await safe_edit_message(msg, f"❌ Muxing Failed!\n\nError:\n```{trimmed_error}```")
        return None
