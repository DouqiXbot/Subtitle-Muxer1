import logging
import time
import asyncio
from pathlib import Path
from helper_func.utils import safe_edit_message, read_stderr
from config import Config

logger = logging.getLogger(__name__)

async def hardmux_vid(vid_filename: str, sub_filename: str, msg, user_settings: dict) -> str:
    """Hardmux video with subtitles using FFmpeg."""
    start = time.time()
    download_dir = Path(Config.DOWNLOAD_DIR)
    vid = download_dir / vid_filename
    sub = download_dir / sub_filename
    output = f"{Path(vid_filename).stem}_hardmuxed.mp4"
    out_location = download_dir / output

    font_path = Path.cwd() / "fonts" / "HelveticaRounded-Bold.ttf"
    if not font_path.exists():
        await safe_edit_message(msg, "❌ Font not found! Please add 'HelveticaRounded-Bold.ttf' in 'fonts' folder.")
        return None

    # Ensure the subtitle path is properly quoted
    formatted_sub = f'"{sub.as_posix()}"'  # Always use double quotes

    # ✅ Resolution Fix (Only 480p, 720p, 1080p allowed)
    resolution_map = {
        "854x480": "scale=854:480",
        "1280x720": "scale=1280:720",
        "1920x1080": "scale=1920:1080"
    }
    
    # Get resolution from user settings or default to 720p
    resolution = user_settings.get("resolution", "1280x720")
    scale_filter = resolution_map.get(resolution, "scale=1280:720")  # Default to 720p

    # ✅ Set default values to prevent KeyError
    crf = user_settings.get("crf", "22")
    preset = user_settings.get("preset", "fast")
    codec = user_settings.get("codec", "libx264")
    font_size = user_settings.get("font_size", "20")

    command = [
        "ffmpeg", "-hide_banner", "-i", str(vid),
        "-vf", (
            f"{scale_filter},subtitles={formatted_sub}:force_style="
            f"'FontName=HelveticaRounded-Bold,FontSize={font_size},"
            f"PrimaryColour={Config.FONT_COLOR},Outline={Config.BORDER_WIDTH}',"
            f"drawtext=text='{Config.WATERMARK}':fontfile='{font_path}':"
            "x=w-tw-10:y=10:fontsize=24:fontcolor=white:borderw=2:bordercolor=black"
        ),
        "-c:v", codec, "-preset", preset,
        "-crf", crf, "-tag:v", "hvc1", "-c:a", "copy", "-y", str(out_location)
    ]

    logger.info(f"🚀 Running FFmpeg command: {' '.join(command)}")

    process = await asyncio.create_subprocess_exec(
        *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    error_output = await read_stderr(start, msg, process)
    await process.wait()

    if process.returncode == 0:
        await safe_edit_message(msg, f"✅ Muxing Completed!\n⏳ Time: `{round(time.time() - start)}s`")
        return output
    else:
        trimmed_error = error_output[-3000:] if len(error_output) > 3000 else error_output
        await safe_edit_message(msg, f"❌ Muxing Failed!\n\nError:\n```{trimmed_error}```")
        return None
