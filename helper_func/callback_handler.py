from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
import logging
from helper_func.muxer import softmux, hardmux  # Ensure correct import

logging.basicConfig(level=logging.DEBUG)

@Client.on_callback_query(filters.regex("softmux|hardmux"))
async def callback_handler(client, query: CallbackQuery):
    logging.debug(f"Received callback data: {query.data}")  # Debugging log
    
    chat_id = query.from_user.id
    await query.answer()  # Acknowledge button press

    if query.data == "softmux":
        await query.message.edit_text("Starting Softmux...")
        await softmux(client, query.message, chat_id)  # Call softmux function
    elif query.data == "hardmux":
        await query.message.edit_text("Starting Hardmux...")
        await hardmux(client, query.message, chat_id)  # Call hardmux function
