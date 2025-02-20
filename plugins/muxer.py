import os
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper_func.ffmpeg import hardmux_vid  # Import FFmpeg muxing function
from config import Config
from helper_func.dbhelper import Database

logger = logging.getLogger(__name__)

db = Database()

# 🔹 Encoding Options
ENCODING_OPTIONS = {
    "crf": ["18", "20", "23"],
    "preset": ["medium", "fast", "veryfast", "ultrafast"],
    "codec": ["libx265", "libx264"],
    "font_size": ["18", "20", "24", "28"],
    "resolution": ["854x480", "1280x720", "1920x1080"]  # Removed "Original"
}

# 🔹 Default Encoding Settings
DEFAULT_SETTINGS = {
    "crf": "22",
    "preset": "fast",
    "codec": "libx264",
    "font_size": "20",
    "resolution": "1280x720"  # Default to 720p
}

# 🔹 User settings storage
user_settings = {}

async def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate dynamic encoding settings keyboard."""
    # Ensure user settings exist
    if user_id not in user_settings:
        user_settings[user_id] = DEFAULT_SETTINGS.copy()
    else:
        # Merge missing keys with default values
        for key, value in DEFAULT_SETTINGS.items():
            user_settings[user_id].setdefault(key, value)

    current_settings = user_settings[user_id]

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"CRF: {current_settings['crf']}", callback_data="setting_crf")],
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

@Client.on_message(filters.command("hardmux") & filters.private)
async def hardmux(client, message):
    """Show encoding settings menu."""
    user_id = message.from_user.id
    keyboard = await get_settings_keyboard(user_id)
    await message.reply_text("⚙️ Configure encoding parameters:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex(r"^setting_(.+)$"))
async def encoding_settings_callback(client, query):
    """Display available encoding options when user clicks a setting."""
    setting_type = query.matches[0].group(1)
    user_id = query.from_user.id

    # Ensure user settings exist
    if user_id not in user_settings:
        user_settings[user_id] = DEFAULT_SETTINGS.copy()

    current_settings = user_settings[user_id]

    buttons = [
        InlineKeyboardButton(
            f"{'✅ ' if option == current_settings.get(setting_type, '') else ''}{option}",
            callback_data=f"set_{setting_type}_{option}"
        ) for option in ENCODING_OPTIONS.get(setting_type, [])
    ]
    buttons.append(InlineKeyboardButton("🔙 Back", callback_data="settings_back"))

    await query.edit_message_text(
        f"Select {setting_type.replace('_', ' ').title()}:",
        reply_markup=InlineKeyboardMarkup([buttons[i:i+2] for i in range(0, len(buttons), 2)])
    )

@Client.on_callback_query(filters.regex(r"^set_(.+)_(.+)$"))
async def set_encoding_parameter(client, query):
    """Save selected encoding setting and return to menu."""
    setting_type, value = query.matches[0].groups()
    user_id = query.from_user.id

    # Ensure user_settings[user_id] exists
    if user_id not in user_settings:
        user_settings[user_id] = DEFAULT_SETTINGS.copy()

    user_settings[user_id][setting_type] = value

    await query.answer(f"{setting_type.replace('_', ' ').title()} set to {value}!")
    keyboard = await get_settings_keyboard(user_id)
    await query.message.edit_text("⚙️ Configure encoding parameters:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex("burn"))
async def start_encoding_process(client, query):
    """Start the encoding process when the user presses 'Start Encoding'."""
    chat_id = query.from_user.id

    # 🔹 Fetch stored filenames
    og_vid_filename = db.get_vid_filename(chat_id)
    og_sub_filename = db.get_sub_filename(chat_id)

    # 🔹 Validation Checks
    text = ''
    if not og_vid_filename or not os.path.exists(os.path.join(Config.DOWNLOAD_DIR, og_vid_filename)):
        text += "First send a Video File\n"
    if not og_sub_filename or not os.path.exists(os.path.join(Config.DOWNLOAD_DIR, og_sub_filename)):
        text += "Send a Subtitle File!"

    if text:
        await client.send_message(chat_id, text)
        return

    # 🔹 Initial message update
    sent_msg = await query.message.edit_text("⚙️ Preparing encoding process...")

    # 🔹 Wait for 10-15 seconds before starting encoding
    await asyncio.sleep(15)

    # 🔹 Start Hardmuxing
    hardmux_filename = await hardmux_vid(og_vid_filename, og_sub_filename, sent_msg, user_settings.get(chat_id, DEFAULT_SETTINGS))

    if not hardmux_filename:
        await sent_msg.edit_text("❌ Encoding Failed!")
        return

    # 🔹 Rename the output file
    final_filename = db.get_filename(chat_id)
    os.rename(os.path.join(Config.DOWNLOAD_DIR, hardmux_filename), os.path.join(Config.DOWNLOAD_DIR, final_filename))

    # 🔹 Upload the final file
    start_time = time.time()
    try:
        await client.send_document(
            chat_id,
            progress=progress_bar,
            progress_args=('Uploading your File!', sent_msg, start_time),
            document=os.path.join(Config.DOWNLOAD_DIR, final_filename),
            caption=final_filename
        )
        await sent_msg.edit_text(f"✅ File Successfully Uploaded!\n⏳ Total Time: {round(time.time() - start_time)} seconds")
    except Exception as e:
        print(e)
        await client.send_message(chat_id, "❌ An error occurred while uploading the file!\nCheck logs for details.")

    # 🔹 Cleanup downloaded files
    path = Config.DOWNLOAD_DIR + '/'
    for file in [og_sub_filename, og_vid_filename, final_filename]:
        if file and os.path.exists(path + file):
            os.remove(path + file)

    db.erase(chat_id)
