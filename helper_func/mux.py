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


async def hardmux_vid(vid_filename, sub_filename, msg, add_logo=False, logo_path=None):
    start = time.time()
    vid = os.path.join(Config.DOWNLOAD_DIR, vid_filename)
    sub = os.path.join(Config.DOWNLOAD_DIR, sub_filename)

    output = f"{os.path.splitext(vid_filename)[0]}_hardmuxed.mp4"
    out_location = os.path.join(Config.DOWNLOAD_DIR, output)

    font_path = os.path.join('fonts', 'HelveticaRounded-Bold.ttf')
    if not os.path.exists(font_path):
        await msg.edit(f"Font file not found at {font_path}. Please ensure the font file exists.")
        return False

    sub = f'"{sub}"' if " " in sub else sub

    vf_filters = [f"subtitles={sub}:force_style='FontName={font_path},FontSize={Config.FONT_SIZE},PrimaryColour={Config.FONT_COLOR},BackColour={Config.BORDER_COLOR},Outline={Config.BORDER_WIDTH}'"]

    if add_logo and logo_path:
        if not os.path.exists(logo_path):
            await msg.edit(f"Logo file not found at {logo_path}. Please ensure the logo file exists.")
            return False
        vf_filters.append(f"movie={logo_path} [logo]; [in][logo] overlay=W-w-10:10 [out]")

    vf = ",".join(vf_filters)

    command = [
        'ffmpeg', '-hide_banner',
        '-i', vid,
        '-vf', vf,
        '-c:v', 'libx265', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p10le',
        '-c:a', 'copy',
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
