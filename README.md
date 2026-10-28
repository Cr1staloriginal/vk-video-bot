# VK Video Bot

Python bot for a VK community that accepts links to publicly accessible videos, offers available quality choices, downloads permitted content, and sends the result as a VK message document.

> MVP status: upload/delivery must be verified with your own VK community and current VK limits before public launch. The bot does not bypass DRM, private access controls, or paywalls.

## Features
- VK Bots Long Poll (`message_new`)
- Quality selection (1080p, 720p, 480p)
- `yt-dlp` for supported public sources and direct HTTP(S) links
- VK Documents API delivery
- File size/duration limits and bounded download concurrency
- Basic URL validation against local/private network addresses
- Temporary-file cleanup
- Secrets configured through `.env`

## Requirements
- Python 3.10+
- A VK community you administer
- Community token with message permission
- Community messages enabled and Bots Long Poll `message_new` event enabled
- FFmpeg for merging separate audio/video streams

## Local setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```
Set `VK_TOKEN` and `VK_GROUP_ID` in `.env`. Never commit `.env` or share the token.

Run: `python -m app.main`

Tests: `pytest -q`

## VPS / systemd
Install Python 3.10+, FFmpeg, and dependencies. Run the app under a dedicated unprivileged user. Keep `.env` outside version control with permissions `600`.

Example service file `/etc/systemd/system/vk-video-bot.service`:
```ini
[Unit]
Description=VK Video Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=vkbot
Group=vkbot
WorkingDirectory=/opt/vk-video-bot
EnvironmentFile=/opt/vk-video-bot/.env
ExecStart=/opt/vk-video-bot/.venv/bin/python -m app.main
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/vk-video-bot/downloads
UMask=0077

[Install]
WantedBy=multi-user.target
```

## Important notes
- No downloader supports literally every website; site support and available formats can change.
- Do not use cookies or bypass DRM, paywalls, private access controls, or platform restrictions.
- Only download content you have permission to save.
- URL validation is a first layer only. For public deployment, enforce outbound network restrictions at the OS/container firewall to prevent SSRF and DNS rebinding.
- VK may impose dynamic upload limits. The configured file limit is conservative but does not guarantee VK acceptance.
- This is an MVP; test with a small permitted video in your own community before public launch.

## Official references
- VK Bots Long Poll: https://dev.vk.ru/ru/api/bots-long-poll/getting-started
- Community token: https://dev.vk.ru/ru/api/access-token/community-token
- `messages.send`: https://dev.vk.ru/ru/method/messages.send
- VK API schema: https://github.com/VKCOM/vk-api-schema
- yt-dlp: https://github.com/yt-dlp/yt-dlp
