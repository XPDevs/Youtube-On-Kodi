# My YouTubers

A custom, unofficial Kodi addon to browse YouTube channels, search videos, and stream or download them — without a Google/YouTube API key or login.

## Disclaimer

- This addon is **not made by, affiliated with, or endorsed by Google LLC or YouTube, LLC**. It is an unofficial, custom-made addon.
- "YouTube" and all related trademarks are the property of their respective owners.
- Streaming or downloading videos may be subject to YouTube's Terms of Service and the content creator's wishes. Use it at your own risk.
- This project is provided "as is", without warranty of any kind.

## Features

- Browse channels defined in `channels.conf`
- Search YouTube and search within a channel
- Stream videos in up to 720p
- Download videos to the addon's downloads folder (with progress)
- Manage downloads from the addon (play or delete)

## Requirements

- Kodi 19+ (Matrix) or newer with Python 3
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — **you must provide your own copy**, see below
- ffmpeg (optional, only needed for downloads that require merging)

## Providing your own yt-dlp

The yt-dlp binary is **not** included in this repository. Drop a `yt-dlp` executable into:

```
resources/bin/yt-dlp
```

Alternatively, install yt-dlp somewhere on the system `PATH`. The addon will use the bundled copy first and fall back to one found on `PATH`.

Note: on LibreELEC, where there is no package manager, download the yt-dlp standalone binary and place it at `resources/bin/yt-dlp`.

## Installation

1. Download or build the addon folder `plugin.video.myyoutubers/`.
2. Copy it to Kodi's addon folder, e.g. `/storage/.kodi/addons/plugin.video.myyoutubers/`.
3. Restart Kodi, or install it via "Install from zip".

## Configuration

Add channels to `resources/channels.conf` (one per line):

```
# One channel per line. Values: handle (@name), channel URL, channel ID, or plain name.
# Optional display name after "|".
@ExampleChannel | Example Channel
```

You can also add and remove channels from the addon's own menu. Your channel list is stored in the addon's profile folder, not in this file.

## License

No license is implied; this is a personal, custom project.
