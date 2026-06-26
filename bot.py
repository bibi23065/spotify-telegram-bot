import asyncio
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_DOWNLOADS", "3"))

SPOTIFY_URL_RE = re.compile(
    r"https?://open\.spotify\.com/(track|album|playlist|artist)/[a-zA-Z0-9]+"
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

semaphore = asyncio.Semaphore(MAX_CONCURRENT)


async def health_handler(request: web.Request) -> web.Response:
    return web.Response(text="OK", status=200)


async def start_health_server() -> None:
    app = web.Application()
    app.router.add_get("/", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Health server running on port %s", PORT)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🎧 Spotify Downloader Bot\n\n"
        "Send me any Spotify URL (track, album, playlist, or artist) "
        "and I'll download it as an MP3 file for you.\n\n"
        "Type /help for more info."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📋 Commands:\n"
        "/start - Welcome message\n"
        "/help - This help message\n\n"
        "Just send a Spotify URL to download it!"
    )


async def download_spotify(url: str, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with semaphore:
        temp_dir = tempfile.mkdtemp()
        msg = None
        try:
            msg = await context.bot.send_message(chat_id, "📥 Downloading...")
            logger.info("Starting download: %s", url)

            output_template = str(Path(temp_dir) / "{title} - {artist}.{output-ext}")
            proc = await asyncio.create_subprocess_exec(
                "spotdl", "download", url,
                "--output", output_template,
                "--format", "mp3",
                "--bitrate", "320k",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            logger.info("spotdl stdout: %s", stdout.decode().strip())
            if proc.returncode != 0:
                error_msg = stderr.decode().strip() or "Unknown error"
                logger.error("spotdl failed (rc=%d): %s", proc.returncode, error_msg)
                await context.bot.edit_message_text(
                    f"❌ Download failed:\n{error_msg[:500]}",
                    chat_id,
                    msg.message_id,
                )
                return

            mp3_files = list(Path(temp_dir).rglob("*.mp3"))

            if not mp3_files:
                all_files = list(Path(temp_dir).rglob("*"))
                logger.warning("No .mp3 files. All files in temp_dir: %s", [f.name for f in all_files if f.is_file()])
                audio_exts = (".mp3", ".webm", ".m4a", ".opus", ".ogg", ".flac")
                mp3_files = [f for f in all_files if f.suffix.lower() in audio_exts]

            if not mp3_files:
                stderr_text = stderr.decode().strip()
                await context.bot.edit_message_text(
                    f"❌ No audio files found.\n\nDebug info:\n```\n{stderr_text[:300]}\n```",
                    chat_id,
                    msg.message_id,
                )
                return

            await context.bot.edit_message_text(
                f"📤 Sending {len(mp3_files)} file(s)...",
                chat_id,
                msg.message_id,
            )

            for mp3 in mp3_files:
                file_size = mp3.stat().st_size
                if file_size > 50 * 1024 * 1024:
                    await context.bot.send_message(
                        chat_id,
                        f"⚠️ Skipping {mp3.name} (exceeds 50MB Telegram limit)",
                    )
                    continue

                with open(mp3, "rb") as audio_file:
                    await context.bot.send_audio(
                        chat_id=chat_id,
                        audio=audio_file,
                        title=mp3.stem,
                    )

            if len(mp3_files) == 1:
                await context.bot.edit_message_text("✅ Done!", chat_id, msg.message_id)
            else:
                await context.bot.edit_message_text(
                    f"✅ Sent {len(mp3_files)} file(s)!", chat_id, msg.message_id
                )

        except Exception as e:
            logger.error("Download error: %s", e)
            error_text = f"❌ An error occurred: {str(e)[:500]}"
            if msg:
                await context.bot.edit_message_text(error_text, chat_id, msg.message_id)
            else:
                await context.bot.send_message(chat_id, error_text)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    match = SPOTIFY_URL_RE.search(text)
    if not match:
        await update.message.reply_text(
            "❌ That doesn't look like a valid Spotify URL.\n\n"
            "Please send a link like:\n"
            "https://open.spotify.com/track/...\n"
            "https://open.spotify.com/album/...\n"
            "https://open.spotify.com/playlist/..."
        )
        return

    url = match.group(0)
    asyncio.create_task(download_spotify(url, update.effective_chat.id, context))


def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        raise SystemExit("TELEGRAM_BOT_TOKEN is required")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(start_health_server())

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
