# Youtube On Kodi

A custom, unofficial YouTube browser for Kodi. No login, no API key.

**Disclaimer:** this addon is not made by, affiliated with, or endorsed by Google or YouTube. It is an unofficial, custom-made addon. "YouTube" and related trademarks belong to their owners. Streaming or downloading videos may be subject to YouTube's Terms of Service and the wishes of the content creators. Use it at your own risk. The project is provided "as is", with no warranty of any kind.

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

**New in this version – smarter caching & resilience:**
- **Intelligent caching:** channels are cached on first visit for near-instant navigation. Caches automatically refresh every 24 hours to keep content current, and a manual re-cache button is provided for on-demand updates.
- **Automatic cache cleanup:** orphaned channel files and old search results are deleted automatically on startup or daily, with a configurable limit on how many search caches to keep.
- **Full configurability:** all cache durations, video refresh intervals, search retention, and retry cooldowns are fully adjustable via addon settings.
- **Resilient operation:** if YouTube fails to respond, the addon keeps your old cached playlists and videos instead of showing empty lists. A built-in cooldown prevents hammering failing requests.
- **Data integrity:** atomic writes prevent file corruption, and resume logic has been refined to only prompt when truly needed.
- **Performance boost:** the Popular section and video metadata are cached for instant loading and snappier playlist additions.

## Requirements

- Kodi 19+ (Matrix) or newer, with Python 3
- **yt-dlp** – see below for how it is supplied
- ffmpeg, optional. Only needed for downloads that require merging

## yt-dlp: bundled releases vs. source builds

**If you use one of the official release archives (`.zip` from the Releases page), yt-dlp is already bundled inside the addon.** You do not need to do anything – it works out of the box.

**If you compile the addon from scratch** (e.g., cloning the git repository and building yourself), the yt-dlp binary is *not* included in the source tree. In that case, you must provide your own copy:

- Download the standalone yt-dlp binary from [https://github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp). The currently recommended version is **2026.03.17**.
- Place it as `resources/bin/yt-dlp` inside the addon folder, or install it somewhere on your system `PATH` – the addon checks the bundled copy first, then falls back to `PATH`.

For LibreELEC users building from source: there is no package manager, so download the standalone binary and place it at `resources/bin/yt-dlp`. Make sure it is executable (`chmod +x`).

## Installation

**Recommended:** download the latest release `.zip` from the Releases page – it includes yt-dlp and is ready to use. Install it via Kodi's *Install from zip*.

**From source (for developers):**
1. Clone or download this repository.
2. Provide yt-dlp as described above (download the recommended version).
3. Copy the addon folder to Kodi's addon directory:

   ```
   cp -r plugin.video.myyoutubers /storage/.kodi/addons/
   ```

4. Restart Kodi.

## Configuration

Channels live in `resources/channels.conf`, one per line:

```
# One channel per line. Values: handle (@name), channel URL, channel ID, or plain name.
# Optional display name after "|".
@ExampleChannel | Example Channel
```

Your personal channel list is stored in the addon's profile folder and is managed through the addon menu (*Add YouTuber* / *Remove YouTuber*).

The addon settings (accessible via Kodi's addon info page) let you fine-tune all caching parameters, including retention periods, refresh intervals, search cache limits, and request cooldowns to suit your preferences.

## Troubleshooting

If something fails, check the addon's `error.log` (in the Kodi addon profile folder) and look at the on-screen error notification. Most issues come from a missing or outdated `yt-dlp` (especially if building from source) or a blocked network request. If you experience stale data, use the manual re-cache button or adjust the cache refresh intervals in the settings.

## License

Licensed under the [GNU General Public License v2.0 or later](LICENSE).
