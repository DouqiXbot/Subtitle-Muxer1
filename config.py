import os

class Config:
    # Font Configuration
    FONT_NAME = "HelveticaRounded-Bold"  # Default font name
    FONT_SIZE = 20       # Default font size
    FONT_COLOR = "&H00FFFFFF"  # ARGB format (White)
    BORDER_COLOR = "&H00000000"  # ARGB format (Black)
    BORDER_WIDTH = 1.5

    # Logo Paths (inside the class)
    LOGO_PATHS = {
        "default": "logos/logo1.png",
        "12345678": "logos/logo1.png",
        "87654321": "logos/logo1.png"
    }

    # Bot Configuration
    BOT_TOKEN = os.environ.get('BOT_TOKEN', None)
    APP_ID = os.environ.get('APP_ID', None)
    API_HASH = os.environ.get('API_HASH', None)

    # Comma-separated user IDs of users who are allowed to use the bot
    ALLOWED_USERS = [x.strip() for x in os.environ.get('ALLOWED_USERS', '1098504493').split(',')]

    # Download Directory
    DOWNLOAD_DIR = 'downloads'
