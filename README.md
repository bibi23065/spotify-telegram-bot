# Spotify Downloader Telegram Bot

A Telegram bot that downloads Spotify tracks, albums, playlists, and artists as MP3 files using the `spotdl` CLI tool.

## Features

- Download individual tracks, albums, playlists, and artist discographies
- 320kbps MP3 output with metadata and album art
- Progress updates during download
- Free deployment on Render.com

## Deployment on Render

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Create Bot Token

1. Open Telegram, search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the bot token

### 3. Get Spotify API Credentials

1. Go to https://developer.spotify.com/dashboard
2. Click **Create App**
3. Fill in: Name = `spotdl-bot`, Description = anything
4. Copy the **Client ID** and **Client Secret**

### 4. Deploy on Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Web Service**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `spotify-telegram-bot`
   - **Runtime**: `Docker`
   - **Instance Type**: Free
5. Add Environment Variables:
   - `TELEGRAM_BOT_TOKEN` = Your bot token from BotFather
   - `SPOTIFY_CLIENT_ID` = Your Spotify Client ID
   - `SPOTIFY_CLIENT_SECRET` = Your Spotify Client Secret
6. Click **Create Web Service**

### 4. Test the Bot

1. Open your bot in Telegram
2. Send `/start`
3. Paste a Spotify URL: `https://open.spotify.com/track/...`
4. Wait for the MP3 download

## Local Development

```bash
docker build -t spotdl-bot .
docker run -e TELEGRAM_BOT_TOKEN=your_token spotdl-bot
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | - | Bot token from BotFather |
| `SPOTIFY_CLIENT_ID` | Yes | - | Spotify API Client ID |
| `SPOTIFY_CLIENT_SECRET` | Yes | - | Spotify API Client Secret |
| `PORT` | No | `8080` | Health check port (set by Render) |
| `MAX_CONCURRENT_DOWNLOADS` | No | `3` | Max parallel downloads |

## Limitations

- Render free tier sleeps after 15 min inactivity (~30s cold start)
- Telegram file size limit: 50MB per file
- Source audio quality capped at ~128kbps (upscaled to 320kbps output)
