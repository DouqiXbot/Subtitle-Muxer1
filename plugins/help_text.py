# (c) DevXkirito 

# Logging
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)
logging.getLogger('pyrogram').setLevel(logging.WARNING)

# Start Command
@Client.on_message(filters.command(['start']))
async def start(bot, update):
    user_name = update.from_user.first_name  # Get user's name

    if str(update.from_user.id) not in Config.ALLOWED_USERS:
        return await bot.send_message(
            chat_id=update.chat.id,
            text="🚫 You are not authorized to use this bot.",
            reply_to_message_id=update.id
        )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Source Code", url="https://github.com/your-repo")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
         InlineKeyboardButton("📢 Updates", url="https://t.me/DonghuaHindi")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])

    await bot.send_photo(
        chat_id=update.chat.id,
        photo="https://envs.sh/EwN.jpg",  # Replace with actual image URL or file path
        caption=(
            f"**Hey {user_name}** 👋\n\n"
            "**WELCOME TO VidBurner**\n\n"
            "**I will help you add subtitles to videos.**\n\n"
            "**Created by 💕 [@CHS ANIME](https://t.me/DonghuaHindi)**"
        ),
        reply_markup=buttons
    )

# Help Command (Callback)
@Client.on_callback_query(filters.regex("help"))
async def help_callback(bot, query):
    await query.answer()  # Confirm button press (faster response)
    
    help_text = (
        "👋 **I am** VidBurner\n\n"
        "**Welcome to the Help Section**\n\n"
        "1️⃣ Send a Video File.\n"
        "2️⃣ Send a Subtitle File. (ass or srt)\n"
        "3️⃣ Select the Mux Type!\n\n"
        "⚠️ **Note:** Only English fonts are supported in Hardmux.\n"
        "Other fonts will appear as empty blocks in the video!\n\n"
        "Created by 💕 CHS ANIME"
    )

    asyncio.create_task(query.message.edit_text(
        text=help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="start")]
        ])
    ))

# About Command (Callback)
@Client.on_callback_query(filters.regex("about"))
async def about_callback(bot, query):
    await query.answer()  # Confirm button press (faster response)

    about_text = (
        "👋 **About Me**\n\n"
        "I am **VidBurner**, a bot designed to help you **add subtitles to videos** easily!\n"
        "I support both **softmux** and **hardmux** methods.\n\n"
        "⚡ **Features:**\n"
        "- Supports `.srt` and `.ass` subtitle formats.\n"
        "- High-speed video processing.\n"
        "- Easy-to-use commands.\n\n"
        "📢 **Stay updated:** [Update Channel](https://t.me/DonghuaHindi)\n"
        "💻 **Developed by:** @Blaze_Techz"
    )

    asyncio.create_task(query.message.edit_text(
        text=about_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="start")]
        ])
    ))

# Back to Start Command (Callback)
@Client.on_callback_query(filters.regex("start"))
async def back_to_start(bot, query):
    await query.answer()  # Confirm button press (faster response)
    
    user_name = query.from_user.first_name  # Get user's name

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Source Code", url="https://github.com/your-repo")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
         InlineKeyboardButton("📢 Updates", url="https://t.me/DonghuaHindi")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])

    asyncio.create_task(query.message.edit_caption(  # Faster execution
        caption=(
            f"**Hey {user_name}** 👋\n\n"
            "**WELCOME TO VidBurner**\n\n"
            "**I will help you add subtitles to videos.**\n\n"
            "**Created by 💕 [@CHS ANIME](https://t.me/DonghuaHindi)**"
        ),
        reply_markup=buttons
    ))
