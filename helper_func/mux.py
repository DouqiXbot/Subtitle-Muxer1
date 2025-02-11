from config import Config
import time
import re
import asyncio
import os

progress_pattern = re.compile(
    r'(frame|fps|size|time|bitrate|speed)\s*\=\s*(\S+)'
)

def parse_progress(line):
    return {key: value for key, value in progress_pattern.findall(line)}

async def readlines(stream):
    pattern = re.compile(br'[\r\n]+')
    data = bytearray()
    while not stream.at_eof():
        lines = pattern.split(data)
        data[:] = lines.pop(-1)
        for line in lines:
            yield line
        data.extend(await stream.read(1024))

async def read_stderr(start, msg, process):
    error_log = []
    async for line in readlines(process.stderr):
        line = line.decode('utf-8')
        error_log.append(line)
        progress = parse_progress(line)
        if progress:
            text = f"PROGRESS\nSize: {progress.get('size', 'N/A')}\nTime: {progress.get('time', 'N/A')}\nSpeed: {progress.get('speed', 'N/A')}"
            try:
                await msg.edit(text)
            except:
                pass
    return "\n".join(error_log)

async def softmux_vid(vid_filename, sub_filename, msg):
    start = time.time()
    vid = os.path.join(Config.DOWNLOAD_DIR, vid_filename)
    sub = os.path.join(Config.DOWNLOAD_DIR, sub_filename)

    output = f"{os.path.splitext(vid_filename)[0]}_muxed.mkv"
    out_location = os.path.join(Config.DOWNLOAD_DIR, output)

    sub_ext = sub_filename.split('.')[-1]

    command = [
        'ffmpeg', '-hide_banner',
        '-i', vid,
        '-i', sub,
        '-map', '1:0', '-map', '0',
        '-disposition:s:0', 'default',
        '-c:v', 'copy',
        '-c:a', 'copy',
        '-c:s', sub_ext,
        '-y', out_location
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    error_output = await read_stderr(start, msg, process)

    if process.returncode == 0:
        await msg.edit(f'Muxing Completed Successfully!\nTime taken: {round(time.time() - start)}s')
        return output
    else:
        await msg.edit(f'An Error occurred while Muxing!\n\nError:\n```{error_output}```')
        return False

async def hardmux_vid(vid_filename, sub_filename, msg):
    start = time.time()
    vid = os.path.join(Config.DOWNLOAD_DIR, vid_filename)
    sub = os.path.join(Config.DOWNLOAD_DIR, sub_filename)

    output = f"{os.path.splitext(vid_filename)[0]}_hardmuxed.mp4"
    out_location = os.path.join(Config.DOWNLOAD_DIR, output)

    # Check if font exists
    font_path = f"/usr/share/fonts/truetype/custom/{Config.FONT_NAME}.ttf"
    if not os.path.exists(font_path):
        font_path = Config.FONT_NAME  # Use font name fallback

    # Ensure subtitle path is correctly formatted
    sub = f'"{sub}"' if " " in sub else sub

    command = [
        'ffmpeg', '-hide_banner',
        '-i', vid,
        '-vf', f"subtitles={sub}:force_style='FontName={font_path},FontSize={Config.FONT_SIZE},PrimaryColour={Config.FONT_COLOR},BackColour={Config.BORDER_COLOR},Outline={Config.BORDER_WIDTH}'",
        '-c:v', 'h264',
        '-map', '0:v:0',
        '-map', '0:a:0?',
        '-preset', 'ultrafast',
        '-y', out_location
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    error_output = await read_stderr(start, msg, process)

    if process.returncode != 0:
    error_output = (await process.stderr.read()).decode('utf-8')
    
    # Trim error output to fit in Telegram's limit (4096 characters)
    trimmed_error = error_output[-3000:] if len(error_output) > 3000 else error_output
    
    await msg.edit(f'An Error occurred while Muxing!\n\nError (last part shown):\n```{trimmed_error}```')
    return False
