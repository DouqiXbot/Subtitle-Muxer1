import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyrogram import Client
from pyrogram.types import CallbackQuery
from helper_func.dbhelper import Database as Db
from plugins.muxer import softmux_vid as softmux, hardmux_vid as hardmux  # Import softmux & hardmux from muxxer.py

db = Db()

@Client.on_callback_query()
async def callback_handler(client, callback_query: CallbackQuery):
    data = callback_query.data
    chat_id = callback_query.message.chat.id

    if data == "softmux":
        await callback_query.answer("Softmux started!", show_alert=False)
        await softmux(client, callback_query.message)  # Call function directly

    elif data == "hardmux":
        await callback_query.answer("Hardmux started!", show_alert=False)
        await hardmux(client, callback_query.message)  # Call function directly
