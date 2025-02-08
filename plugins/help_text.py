# (c) mohdsabahat

# Logging
import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

import os
from pyrogram import Client, filters  # Fixed import
from chat import Chat
from config import Config

logging.getLogger('pyrogram').setLevel(logging.WARNING)

@Client.on_message(filters.command(['help']))
async def help_user(bot, update):
    if str(update.from_user.id) in Config.ALLOWED_USERS:
        await bot.send_message(
            chat_id=update.chat.id,
            text=Chat.HELP_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_to_message_id=update.id  # Fixed message_id
        )
    else:
        await bot.send_message(
            chat_id=update.chat.id,
            text=Chat.NO_AUTH_USER,
            reply_to_message_id=update.id  # Fixed message_id
        )

@Client.on_message(filters.command(['start']))
async def start(bot, update):
    if str(update.from_user.id) not in Config.ALLOWED_USERS:
        return await bot.send_message(
            chat_id=update.chat.id,
            text=Chat.NO_AUTH_USER,
            reply_to_message_id=update.id  # Fixed message_id
        )

    await bot.send_message(
        chat_id=update.chat.id,
        text=Chat.START_TEXT,
        reply_to_message_id=update.id  # Fixed message_id
    )
