# Contributing

Thanks for wanting to help with Youtube On Kodi.

This is a small, personal, unofficial project. It has no strict rules, but a few notes below will make things go smoother.

## Reporting a problem or asking for a feature

Open an issue and include:

- The exact steps to reproduce the problem.
- What you expected to happen and what actually happened.
- Your setup: Kodi version, OS (e.g. LibreELEC), whether yt-dlp is bundled or on `PATH`, and anything in `error.log`.

## Building and testing

The addon is a single Kodi Python plugin:

- `default.py` is the entry point and handles routing.
- `resources/lib/kanyt.py` has the shared logic (channel resolution, video listing, streaming, downloads).
- `resources/channels.conf` is the default channel list.

There is no build step. To test, copy the addon folder into Kodi's addon directory and restart Kodi.

The repository does not bundle the yt-dlp binary. For local testing, drop an executable `yt-dlp` at `resources/bin/yt-dlp` or make sure it is on your `PATH`. It is ignored by git (see `.gitignore`).

## Submitting changes

1. Fork the repository and create a feature branch.
2. Keep changes focused and match the existing code style.
3. Bump the `version` attribute in `addon.xml` and add a note to `CHANGELOG.md`.
4. Open a pull request describing what you changed and why.

## License

By contributing you agree your contributions are licensed under the same terms as the project (GPL-2.0-or-later, see `LICENSE`).
