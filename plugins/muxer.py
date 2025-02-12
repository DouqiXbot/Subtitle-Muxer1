from pyrogram import Client, filters
from helper_func.progress_bar import progress_bar
from helper_func.dbhelper import Database as Db
from helper_func.mux import softmux_vid, hardmux_vid
from config import Config
import time
import os

db = Db()

async def _check_user(filt, c, m):
    chat_id = str(m.from_user.id)
    return chat_id in Config.ALLOWED_USERS

check_user = filters.create(_check_user)

@Client.on_message(filters.command('softmux') & check_user & filters.private)
async def softmux(client, message):
    chat_id = message.from_user.id
    og_vid_filename = db.get_vid_filename(chat_id)
    og_sub_filename = db.get_sub_filename(chat_id)
    
    if not og_vid_filename or not og_sub_filename:
        missing = []
        if not og_vid_filename:
            missing.append("Video File")
        if not og_sub_filename:
            missing.append("Subtitle File")
        await client.send_message(chat_id, f"First send a {', '.join(missing)}!")
        return

    text = "Your File is Being Soft Subbed. This should be done in a few seconds!"
    sent_msg = await client.send_message(chat_id, text)

    softmux_filename = await softmux_vid(og_vid_filename, og_sub_filename, sent_msg)
    if not softmux_filename:
        return

    final_filename = db.get_filename(chat_id)
    os.rename(os.path.join(Config.DOWNLOAD_DIR, softmux_filename), os.path.join(Config.DOWNLOAD_DIR, final_filename))

    start_time = time.time()
    try:
        await client.send_document(
            chat_id, 
            progress=progress_bar, 
            progress_args=("Uploading your File!", sent_msg, start_time), 
            document=os.path.join(Config.DOWNLOAD_DIR, final_filename),
            caption=final_filename
        )
        await sent_msg.edit(f"File Successfully Uploaded!\nTotal Time taken: {round(time.time() - start_time)} seconds")
    except Exception as e:
        print(e)
        await client.send_message(chat_id, "An error occurred while uploading the file!\nCheck logs for details.")

    path = Config.DOWNLOAD_DIR
    os.remove(os.path.join(path, og_sub_filename))
    os.remove(os.path.join(path, og_vid_filename))
    try:
        os.remove(os.path.join(path, final_filename))
    except:
        pass

    db.erase(chat_id)

@Client.on_message(filters.command('hardmux') & check_user & filters.private)
async def hardmux(client, message):
    chat_id = message.from_user.id
    og_vid_filename = db.get_vid_filename(chat_id)
    og_sub_filename = db.get_sub_filename(chat_id)

    if not og_vid_filename or not og_sub_filename:
        missing = []
        if not og_vid_filename:
            missing.append("Video File")
        if not og_sub_filename:
            missing.append("Subtitle File")
        await client.send_message(chat_id, f"First send a {', '.join(missing)}!")
        return
    
    # Ask user if they want to add a logo
    sent_msg = await client.send_message(chat_id, "Do you want to add a logo? (Yes/No)")
    
    def check(m):
        return m.from_user.id == chat_id and m.text.lower() in ["yes", "no"]
    
    response = await client.listen(chat_id, filters=filters.text & filters.private, check=check)

    add_logo = response.text.lower() == "yes"
    logo_path = None

    if add_logo:
        await client.send_message(chat_id, "Please send the logo file.")
        logo_msg = await client.listen(chat_id, filters=filters.document & filters.private)
        logo_file = await client.download_media(logo_msg.document)
        logo_path = os.path.join(Config.DOWNLOAD_DIR, logo_file)

    text = "Your File is Being Hard Subbed. This might take a long time!"
    sent_msg = await client.send_message(chat_id, text)

    hardmux_filename = await hardmux_vid(og_vid_filename, og_sub_filename, sent_msg, client, chat_id, add_logo, logo_path)

    if not hardmux_filename:
        return

    final_filename = db.get_filename(chat_id)
    os.rename(os.path.join(Config.DOWNLOAD_DIR, hardmux_filename), os.path.join(Config.DOWNLOAD_DIR, final_filename))

    start_time = time.time()
    try:
        await client.send_video(
            chat_id, 
            progress=progress_bar, 
            progress_args=("Uploading your File!", sent_msg, start_time), 
            video=os.path.join(Config.DOWNLOAD_DIR, final_filename),
            caption=final_filename
        )
        await sent_msg.edit(f"File Successfully Uploaded!\nTotal Time taken: {round(time.time() - start_time)} seconds")
    except Exception as e:
        print(e)
        await client.send_message(chat_id, "An error occurred while uploading the file!\nCheck logs for details.")

    path = Config.DOWNLOAD_DIR
    os.remove(os.path.join(path, og_sub_filename))
    os.remove(os.path.join(path, og_vid_filename))
    try:
        os.remove(os.path.join(path, final_filename))
        if add_logo and logo_path:
            os.remove(logo_path)
    except:
        pass

    db.erase(chat_id)
