FROM python:3.10

# Install required dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fontconfig \
    ttf-mscorefonts-installer \
    && fc-cache -f

# Copy custom fonts
COPY fonts/ /usr/share/fonts/custom/
RUN fc-cache -f -v

# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "muxbot.py"]
