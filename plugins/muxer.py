from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from helper_func.progress_bar import progress_bar
from helper_func.dbhelper import Database as Db
from helper_func.ffmpeg import hardmux_vid
from config import Config
import time
import os
import json

db = Db()

async def _check_user(filt, c, m):
    chat_id = str(m.from_user.id)
    return chat_id in Config.ALLOWED_USERS

check_user = filters.create(_check_user)

# Store user preferences (Temporary Storage)
user_preferences = {}

# --- 🔹 Dynamic Button Handlers ---
async def get_dynamic_keyboard(chat_id):
    """Generate InlineKeyboard with user preferences."""
    if chat_id not in user_preferences:
        user_preferences[chat_id] = {
            "codec": "libx264",
            "crf": "22",
            "bit_depth": "8bit",
            "resolution": "1280x720",
            "font_size": "20",
            "watermark": "CHS Anime"
        }

    prefs = user_preferences[chat_id]

    keyboard = [
        [
            InlineKeyboardButton(f"🎞 Codec: {prefs['codec']}", callback_data="set_codec"),
            InlineKeyboardButton(f"📝 CRF: {prefs['crf']}", callback_data="set_crf")
        ],
        [
            InlineKeyboardButton(f"🌟 Bit Depth: {prefs['bit_depth']}", callback_data="set_bitdepth"),
            InlineKeyboardButton(f"📺 Resolution: {prefs['resolution']}", callback_data="set_resolution")
        ],
        [
            InlineKeyboardButton(f"🔤 Font Size: {prefs['font_size']}", callback_data="set_fontsize"),
            InlineKeyboardButton(f"💧 Watermark: {prefs['watermark']}", callback_data="set_watermark")
        ],
        [InlineKeyboardButton("✅ Start Hardmux", callback_data="start_hardmux")]
    ]

    return InlineKeyboardMarkup(keyboard)

@Client.on_message(filters.command('set_preferences') & check_user & filters.private)
async def set_preferences(client, message):
    """Send dynamic buttons for users to select preferences."""
    chat_id = message.from_user.id
    
    # ✅ Initialize defaults if not present
    if chat_id not in user_preferences:
        user_preferences[chat_id] = {
            "codec": "libx264",
            "crf": "22",
            "bit_depth": "8bit",
            "resolution": "1280x720",
            "font_size": "20",
            "watermark": "CHS Anime"
        }

    await message.reply_text("🔧 **Select Encoding Preferences:**", reply_markup=await get_dynamic_keyboard(chat_id))
    
@Client.on_callback_query(filters.regex(r"set_(.+)"))
async def update_preferences(client, callback: CallbackQuery):
    """Handle preference updates from dynamic buttons."""
    chat_id = callback.from_user.id
    option = callback.data.split("_")[1]

    options_map = {
        "codec": ["libx264", "libx265"],
        "crf": ["18", "22", "28"],
        "bitdepth": ["8bit", "10bit"],
        "resolution": ["854x480", "1280x720", "1920x1080"],
        "fontsize": ["16", "20", "24"],
        "watermark": ["CHS Anime", "Custom Text", "None"]
    }

    current_value = user_preferences[chat_id].get(option, options_map[option][0])
    new_index = (options_map[option].index(current_value) + 1) % len(options_map[option])
    user_preferences[chat_id][option] = options_map[option][new_index]

    await callback.message.edit_text("🔧 **Updated Preferences:**", reply_markup=await get_dynamic_keyboard(chat_id))
    await callback.answer("Updated!")

# --- 🔹 Hardmux Function ---
@Client.on_message(filters.command('hardmux') & check_user & filters.private)
async def hardmux(client, message):
    chat_id = message.from_user.id
    og_vid_filename = db.get_vid_filename(chat_id)
    og_sub_filename = db.get_sub_filename(chat_id)

    # Validation Checks
    text = ''
    if not og_vid_filename or not os.path.exists(os.path.join(Config.DOWNLOAD_DIR, og_vid_filename)):
        text += 'First send a Video File\n'
    if not og_sub_filename or not os.path.exists(os.path.join(Config.DOWNLOAD_DIR, og_sub_filename)):
        text += 'Send a Subtitle File!'
    
    if text:
        await client.send_message(chat_id, text)
        return

    # Show Dynamic Buttons Before Processing
    await message.reply_text("🔧 **Select Encoding Preferences Before Hardmuxing:**", reply_markup=await get_dynamic_keyboard(chat_id))

@Client.on_callback_query(filters.regex("start_hardmux"))
async def start_hardmux(client, callback: CallbackQuery):
    chat_id = callback.from_user.id
    og_vid_filename = db.get_vid_filename(chat_id)
    og_sub_filename = db.get_sub_filename(chat_id)

    if not og_vid_filename or not og_sub_filename:
        await callback.answer("⚠️ Missing files. Please upload them first!", show_alert=True)
        return

    sent_msg = await client.send_message(chat_id, "⏳ Your File is Being Hard Subbed. This might take a long time!")

    hardmux_filename = await hardmux_vid(og_vid_filename, og_sub_filename, sent_msg, user_preferences.get(chat_id, {}))
    if not hardmux_filename:
        return
    
    final_filename = db.get_filename(chat_id)
    os.rename(os.path.join(Config.DOWNLOAD_DIR, hardmux_filename), os.path.join(Config.DOWNLOAD_DIR, final_filename))

    start_time = time.time()
    try:
        await client.send_document(
            chat_id,
            progress=progress_bar,
            progress_args=('Uploading your File!', sent_msg, start_time),
            document=os.path.join(Config.DOWNLOAD_DIR, final_filename),
            caption=final_filename
        )
        await sent_msg.edit(f'✅ File Successfully Uploaded!\n⏳ Time Taken: {round(time.time() - start_time)}s')
    except Exception as e:
        print(e)
        await client.send_message(chat_id, '❌ An error occurred while uploading the file!')

    # Safe Cleanup
    path = Config.DOWNLOAD_DIR + '/'
    if og_sub_filename and os.path.exists(path + og_sub_filename):
        os.remove(path + og_sub_filename)
    if og_vid_filename and os.path.exists(path + og_vid_filename):
        os.remove(path + og_vid_filename)
    if final_filename and os.path.exists(path + final_filename):
        os.remove(path + final_filename)

    db.erase(chat_id)
    await callback.answer("✅ Hardmuxing Started!")
