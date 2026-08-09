# Contributing

Thank you for your interest in contributing to Youtube On Kodi.

This is a small, personal, unofficial project. Before opening a pull request or issue, please read this guide.

## Code of conduct

Be respectful and constructive. Do not spam, troll, or post personal data.

## Bug reports and feature requests

Open an [issue](https://github.com/USER/REPO/issues) and include:

- The exact steps to reproduce the problem.
- What you expected to happen and what actually happened.
- Your environment: Kodi version, OS (e.g. LibreELEC), whether yt-dlp is bundled or on `PATH`, and any output from `error.log`.

## Development setup

The addon is a single Kodi Python plugin:

- `default.py` — plugin entry point and routing.
- `resources/lib/kanyt.py` — shared logic (channel resolution, video listing, streaming, downloads).
- `resources/channels.conf` — default channel list.

There is no build step. To test, copy the addon folder into Kodi's addon directory and restart Kodi.

### Providing yt-dlp

The repository does not bundle the yt-dlp binary. For local testing, drop an executable `yt-dlp` at `resources/bin/yt-dlp` or ensure it is on your `PATH`. It is ignored by git (see `.gitignore`).

## Submitting changes

1. Fork the repository and create a feature branch.
2. Make focused changes and keep the existing code style.
3. Bump the `version` attribute in `addon.xml` and add a note to `CHANGELOG.md`.
4. Open a pull request describing what you changed and why.

## License

By contributing you agree that your contributions are licensed under the same terms as the project (GPL-2.0-or-later, see `LICENSE`).
