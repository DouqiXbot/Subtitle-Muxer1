import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper_func.ffmpeg import hardmux_vid  # Import FFmpeg muxing function
from config import Config

logger = logging.getLogger(__name__)

# 🔹 Encoding Options
ENCODING_OPTIONS = {
    "crf": ["18", "20", "22"],
    "preset": ["medium", "fast", "veryfast", "ultrafast"],
    "codec": ["libx265", "libx264"],
    "font_size": ["18", "20", "24", "28"],
    "resolution": ["480p", "720p", "1080p"]
}

# 🔹 User settings storage
user_settings = {}

async def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate dynamic encoding settings keyboard."""
    default_settings = {"crf": "22", "preset": "fast", "codec": "libx264", "font_size": "20", "resolution": "720p"}
    current_settings = user_settings.get(user_id, default_settings)

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
    current_settings = user_settings.get(user_id, {})

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
    if user_id not in user_settings:
        user_settings[user_id] = {}
    user_settings[user_id][setting_type] = value

    await query.answer(f"{setting_type.title()} set to {value}!")
    keyboard = await get_settings_keyboard(user_id)
    await query.message.edit_text("⚙️ Configure encoding parameters:", reply_markup=keyboard)

@Client.on_callback_query(filters.regex("burn"))
async def start_encoding_process(client, query):
    """Start the encoding process when the user presses 'Start Encoding'."""
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    user_settings[user_id] = user_settings.get(user_id, {
        "crf": "22",
        "preset": "fast",
        "codec": "libx264",
        "font_size": "20",
        "resolution": "720p"
    })

    # 🔹 Check if user uploaded files
    video_file = None
    subtitle_file = None

    async for message in client.get_chat_history(chat_id, limit=10):
        if message.video or message.document:
            video_file = message.video.file_name if message.video else message.document.file_name
        if message.document and message.document.file_name.endswith((".srt", ".ass")):
            subtitle_file = message.document.file_name

    if not video_file or not subtitle_file:
        await query.message.edit_text("❌ Please upload a video and subtitle file first!")
        return

    sent_msg = await query.message.edit_text("⚙️ Preparing encoding process...")

    try:
        # 🔹 Call Hardmux Function
        output_filename = await hardmux_vid(video_file, subtitle_file, sent_msg, user_settings)

        if output_filename:
            await client.send_document(chat_id, document=output_filename, caption="✅ Encoding Completed!")
        else:
            await sent_msg.edit_text("❌ Encoding Failed!")

    except Exception as e:
        logger.error(f"❌ Encoding failed: {e}")
        await sent_msg.edit_text(f"❌ An error occurred:\n`{str(e)}`")
