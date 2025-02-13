# (c) DevXkirito 

# Logging
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

logging.getLogger('pyrogram').setLevel(logging.WARNING)

@Client.on_message(filters.command(['start']))
async def start(bot, update):
    user_name = update.from_user.first_name  # User ka naam lene ke liye

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

@Client.on_callback_query(filters.regex("help"))
async def help_callback(bot, query):
    help_text = (
        "👋 **I am VidBurner**\n\n"
        "**Welcome to the Help Section**\n\n"
        "1️⃣ Send a Video File.\n"
        "2️⃣ Send a Subtitle File. (ass or srt)\n"
        "3️⃣ Select the Mux Type!\n\n"
        "⚠️ **Note:** Only English fonts are supported in Hardmux.\n"
        "Other fonts will appear as empty blocks in the video!\n\n"
        "Created by 💕 CHS ANIME"
    )

    await query.message.edit_text(
        text=help_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="start")]
        ])
    )

@Client.on_callback_query(filters.regex("about"))
async def about_callback(bot, query):
    about_text = (
        "👋 **About Me**\n\n"
        "**I am VidBurner, a bot designed to help you add subtitles to videos easily!**\n"
        "I support both **softmux** and **hardmux** methods.\n\n"
        "⚡ **Features:**\n"
        "- Supports `.srt` and `.ass` subtitle formats.\n"
        "- High-speed video processing.\n"
        "- Easy-to-use commands.\n\n"
        "📢 **Stay updated: [Update Channel](https://t.me/DonghuaHindi)**\n"
        "💻 **Developed by: @Blaze_Techz**"
    )

    await query.message.edit_text(
        text=about_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="start")]
        ])
    )
  
@Client.on_callback_query(filters.regex("start"))
async def back_to_start(bot, query):
    user_name = query.from_user.first_name  # User ka naam phir se lena hai

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Source Code", url="https://github.com/your-repo")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
         InlineKeyboardButton("📢 Updates", url="https://t.me/DonghuaHindi")],
        [InlineKeyboardButton("ℹ️ About", callback_data="about")]
    ])

    await query.message.edit_caption(
        caption=(
            f"**Hey {user_name}** 👋\n\n"
            "**WELCOME TO VidBurner**\n\n"
            "**I will help you add subtitles to videos.**\n\n"
            "**Created by 💕 [@CHS ANIME](https://t.me/DonghuaHindi)**"
        ),
        reply_markup=buttons
    )
