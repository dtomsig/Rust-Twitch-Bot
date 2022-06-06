# Rust-Twitch-Bot

Interesting idea I came up with. This program downloads Rust VODS from twitch to APPDATA. It then processes them and submits it to a voice-to-text service. From this service, it searches the transcript for instances of when streamers say their door code so you can see what's in their base. It will then ping discord.

It's kind of difficult to set up. You have to download the ffmepg.exe program, have a wit and twitch api account, and set up a discord webhook.

The values must be set at the top of the program as shown below.



DISCORD_WEB_HOOK = ''

FFMPEG_FILE_PATH = '' # EXAMPLE: 'C:\\Users\\Diego\\Desktop\\ffmpeg-master-latest-win64-gpl\\bin\\ffmpeg.exe

TWITCH_AUTHORIZATION_KEY = ''

TWITCH_CLIENT_ID = ''

WIT_TOKEN = ''
