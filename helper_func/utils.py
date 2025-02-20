import logging
import time
import asyncio
import re

logger = logging.getLogger(__name__)

# Regex pattern to parse FFmpeg progress
PROGRESS_PATTERN = re.compile(r'(frame|fps|size|time|bitrate|speed)\s*=\s*(\S+)')

def parse_progress(line: str):
    """Parse FFmpeg progress output into a dictionary."""
    return dict(PROGRESS_PATTERN.findall(line))

async def readlines(stream):
    """Asynchronously read lines from a stream."""
    pattern = re.compile(br'[\r\n]+')
    data = bytearray()
    while not stream.at_eof():
        lines = pattern.split(data)
        data[:] = lines.pop(-1)
        for line in lines:
            yield line
        data.extend(await stream.read(1024))

async def safe_edit_message(msg, text: str, retries: int = 1):
    """Safely edit a message with retry logic."""
    for attempt in range(retries + 1):
        try:
            await msg.edit(text)
            return
        except Exception as e:
            logger.warning(f"Edit failed: {e}")
            if "messages.EditMessage" in str(e) and attempt < retries:
                await asyncio.sleep(5)
            else:
                logger.error(f"Failed to edit message after {retries} retries: {e}")
                break

async def read_stderr(start: float, msg, process) -> str:
    """Read FFmpeg stderr and update progress."""
    error_log = []
    last_edit_time = time.time()
    async for line in readlines(process.stderr):
        line_str = line.decode('utf-8', errors='ignore')
        error_log.append(line_str)
        progress = parse_progress(line_str)
        if progress and (time.time() - last_edit_time >= 10):
            text = (
                "🔄 **Processing...**\n"
                f"Size: {progress.get('size', 'N/A')}\n"
                f"Time: {progress.get('time', 'N/A')}\n"
                f"Speed: {progress.get('speed', 'N/A')}"
            )
            await safe_edit_message(msg, text)
            last_edit_time = time.time()
    return "\n".join(error_log)
