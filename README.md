# Youtube On Kodi

A custom, unofficial YouTube browser for Kodi. No login, no API key.

Disclaimer: this addon is not made by, affiliated with, or endorsed by Google or YouTube. It is an unofficial, custom-made addon. "YouTube" and related trademarks belong to their owners. Streaming or downloading videos may be subject to YouTube's Terms of Service and the wishes of the content creators. Use it at your own risk. The project is provided "as is", with no warranty of any kind.

## What it does

- Browse channels defined in `channels.conf`, with "Load more" paging through a channel's videos
- Add or remove channels from the addon menu (handle, URL or channel ID)
- Search YouTube, or search within a specific channel, both with "Load more"
- Popular section: top videos from your channels, sorted by view count
- Selecting a video offers Play or Download
- Stream videos in up to 720p directly in Kodi
- Download videos to the addon's downloads folder, with a live progress bar and cancel
- Downloads manager in the main menu: list saved files, play or delete them
- Error notifications on screen, with details written to `error.log`
- Works on LibreELEC / Raspberry Pi without a JavaScript runtime
- No YouTube login or API key required

## Requirements

- Kodi 19+ (Matrix) or newer, with Python 3
- [yt-dlp](https://github.com/yt-dlp/yt-dlp), you provide your own copy (see below)
- ffmpeg, optional. Only needed for downloads that require merging

## Providing your own yt-dlp

The yt-dlp binary is not bundled with this repository.

Drop an executable `yt-dlp` into `resources/bin/yt-dlp`, or install yt-dlp somewhere on your system `PATH`. The addon uses the bundled copy first and falls back to one found on `PATH`.

For LibreELEC users: there is no package manager, so download the yt-dlp standalone binary and place it at `resources/bin/yt-dlp`.

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

If something fails, check the addon's `error.log` (in the Kodi addon profile folder) and look at the on-screen error notification. Most issues come from a missing or outdated `yt-dlp`, or a blocked network request.

## License

Licensed under the [GNU General Public License v2.0 or later](LICENSE).
