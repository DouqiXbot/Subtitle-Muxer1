from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import os
import pysubs2

app = Client("subtitle_bot")

# Track user states
user_states = {}

# Command: /convert - Show format options
@app.on_message(filters.command("convert"))
async def start_conversion(client, message):
    user_id = message.from_user.id
    user_states[user_id] = {"waiting_for_format": True}  # Mark user as selecting format

    buttons = [
        [InlineKeyboardButton("SRT ➝ ASS", callback_data="format_srt_ass")],
        [InlineKeyboardButton("ASS ➝ SRT", callback_data="format_ass_srt")],
        [InlineKeyboardButton("TXT ➝ ASS", callback_data="format_txt_ass")],
    ]

    await message.reply_text(
        "Select the subtitle format you want to convert:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# Handle format selection
@app.on_callback_query(filters.regex("^format_"))
async def handle_format_selection(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    conversion_type = callback_query.data.replace("format_", "")

    user_states[user_id] = {
        "waiting_for_file": True,
        "conversion_type": conversion_type
    }

    await callback_query.message.edit_text(
        "Now, please send me the subtitle file you want to convert."
    )

# Handle subtitle file upload
@app.on_message(filters.document)
async def handle_subtitle(client, message):
    user_id = message.from_user.id
    user_data = user_states.get(user_id)

    if not user_data or "waiting_for_file" not in user_data:
        await message.reply_text("Please use /convert first and select a format before sending a file.")
        return

    # Download file
    file_path = await message.download()
    conversion_type = user_data["conversion_type"]

    # Perform conversion
    converted_file = None
    if conversion_type == "srt_ass":
        converted_file = convert_srt_to_ass(file_path)
    elif conversion_type == "ass_srt":
        converted_file = convert_ass_to_srt(file_path)
    elif conversion_type == "txt_ass":
        converted_file = convert_txt_to_ass(file_path)

    # Send converted file if successful
    if converted_file:
        await message.reply_document(converted_file, caption="Here is your converted subtitle file.")
        os.remove(converted_file)  # Cleanup after sending

    os.remove(file_path)  # Remove original file
    user_states.pop(user_id, None)  # Reset user state

# Subtitle conversion functions using pysubs2
def convert_srt_to_ass(srt_file):
    subs = pysubs2.load(srt_file, encoding="utf-8")
    output_file = srt_file.replace(".srt", ".ass")
    subs.save(output_file, format="ass")
    return output_file

def convert_ass_to_srt(ass_file):
    subs = pysubs2.load(ass_file, encoding="utf-8")
    output_file = ass_file.replace(".ass", ".srt")
    subs.save(output_file, format="srt")
    return output_file

def convert_txt_to_ass(txt_file):
    with open(txt_file, "r", encoding="utf-8") as file:
        lines = file.readlines()

    subs = pysubs2.Subs()
    start_time = 0
    duration = 3000  # Each line lasts 3 seconds

    for line in lines:
        text = line.strip()
        if text:
            subs.append(pysubs2.Line(start=start_time, end=start_time + duration, text=text))
            start_time += duration + 1000  # 1s gap between lines

    output_file = txt_file.replace(".txt", ".ass")
    subs.save(output_file, format="ass")
    return output_file

app.run()
