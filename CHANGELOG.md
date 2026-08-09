# Changelog

All notable changes to this project are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

[1.2.1]: https://github.com/USER/REPO/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/USER/REPO/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/USER/REPO/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/USER/REPO/releases/tag/v1.0.0
