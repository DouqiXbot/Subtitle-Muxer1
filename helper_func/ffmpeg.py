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

    sub_path = sub.as_posix().replace(":", "\\:")
    formatted_sub = f"'{sub_path}'" if " " in sub.name else sub_path
    scale_filter = f"scale={user_settings['resolution']}," if user_settings["resolution"] != "Original" else ""

    command = [
        "ffmpeg", "-hide_banner", "-i", str(vid),
        "-vf", (
            f"{scale_filter}"
            f"subtitles={formatted_sub}:force_style="
            f"'FontName=HelveticaRounded-Bold,FontSize={user_settings['font_size']},"
            f"PrimaryColour={Config.FONT_COLOR},Outline={Config.BORDER_WIDTH}',"
            f"drawtext=text='{Config.WATERMARK}':fontfile='{font_path}':"
            "x=w-tw-10:y=10:fontsize=24:fontcolor=white:borderw=2:bordercolor=black"
        ),
        "-c:v", user_settings["codec"], "-preset", user_settings["preset"],
        "-crf", user_settings["crf"], "-tag:v", "hvc1", "-c:a", "copy", "-y", str(out_location)
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
