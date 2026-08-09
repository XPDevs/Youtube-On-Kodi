<div align="center">

# Youtube On Kodi

**A custom, unofficial YouTube browser for Kodi — no login, no API key.**

[![Kodi](https://img.shields.io/badge/Kodi-19%2B%20(Matrix)-blue.svg)](https://kodi.tv)
[![License: GPL-2.0-or-later](https://img.shields.io/badge/License-GPL--2.0--or--later-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3-green.svg)](https://python.org)
[![yt-dlp](https://img.shields.io/badge/yt--dlp-required-red.svg)](https://github.com/yt-dlp/yt-dlp)

</div>

> **Disclaimer:** This addon is **not made by, affiliated with, or endorsed by Google LLC or YouTube, LLC**. It is an unofficial, custom-made addon. "YouTube" and all related trademarks are the property of their respective owners. Streaming or downloading videos may be subject to YouTube's Terms of Service and the content creator's wishes — use at your own risk. This project is provided "as is", without warranty of any kind.

---

## Features

- Browse channels defined in `channels.conf` (add/remove them from the addon menu)
- Search YouTube, or search within a specific channel
- Stream videos in up to 720p directly in Kodi
- Download videos to the addon's downloads folder with a live progress bar
- Downloads manager: list saved files, play or delete them
- Works on LibreELEC / Raspberry Pi without a JavaScript runtime

## Requirements

- Kodi 19+ (Matrix) or newer, with Python 3
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — you must provide your own copy (see below)
- ffmpeg — optional; only needed for downloads that require merging

## Providing your own yt-dlp

The yt-dlp binary is **not bundled** with this repository.

Drop an executable `yt-dlp` into:

```
resources/bin/yt-dlp
```

or install yt-dlp somewhere on your system `PATH`. The addon uses the bundled copy first and falls back to one found on `PATH`.

> **LibreELEC users:** there is no package manager, so download the yt-dlp standalone binary and place it at `resources/bin/yt-dlp`.

## Installation

1. Clone or download this repository.
2. Copy the addon folder to Kodi's addon directory:

   ```
   cp -r plugin.video.myyoutubers /storage/.kodi/addons/
   ```

3. Restart Kodi (or use *Install from zip* with a packaged `.zip`).

## Configuration

Channels live in `resources/channels.conf`, one per line:

```
# One channel per line. Values: handle (@name), channel URL, channel ID, or plain name.
# Optional display name after "|".
@ExampleChannel | Example Channel
```

Your personal channel list is stored in the addon's profile folder and is managed through the addon menu (*Add YouTuber* / *Remove YouTuber*).

## Troubleshooting

If something fails, check the addon's `error.log` (in the Kodi addon profile folder) and review the on-screen error notification. Most issues are caused by a missing or outdated `yt-dlp`, or a blocked network request.

## License

Licensed under the [GNU General Public License v2.0 or later](LICENSE).
