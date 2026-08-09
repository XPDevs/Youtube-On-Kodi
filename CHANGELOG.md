# Changelog

## [1.3.0] - 2026-08-09

### Added
- Popular section in the main menu: top videos from your channels, sorted by view count.
- "Load more" button in YouTube search results (works without a JS runtime).

## [1.2.1] - 2026-08-09

### Fixed
- "Load more" now works on systems without a JS runtime (e.g. LibreELEC): the channel video listing no longer requires a bundled node, and falls back to the RSS feed only when yt-dlp fails.

## [1.2.0] - 2026-08-09

### Added
- Download any video with live progress to the addon's downloads folder.
- Downloads manager in the main menu: list saved files, play or delete them.

## [1.1.0] - 2026-08-09

### Added
- Add and remove channels from the addon's main menu.
- Search within a channel.
- Error logging to `error.log` with on-screen notifications.

## [1.0.0] - 2026-08-08

### Added
- Initial release.
- Channel browsing from `channels.conf`.
- YouTube search.
- Video streaming via yt-dlp.
