# Spicetify Manager

A modern, beginner-friendly Windows desktop manager for
[Spicetify](https://spicetify.app/). It detects Spotify and Spicetify, guides
first-time setup, manages common maintenance tasks, and keeps command output
easy to understand.

## Features

- Detects desktop Spotify, Microsoft Store Spotify, and Spicetify
- Installs or upgrades the official Spicetify CLI
- Detects, installs, and safely updates the official Spicetify Marketplace
- Creates backups and applies Spicetify after Spotify updates
- Updates the active theme and restores Spotify when needed
- Safely removes Spicetify from Spotify or fully uninstalls it
- Repairs Spicetify with a guided restore, backup, and apply sequence
- Shows command progress, completion percentages, notifications, and logs
- Downloads and verifies application updates from the official GitHub release
- Includes Standard, Large Text, and High Contrast accessibility modes
- Stores settings and logs in the current user's local application-data folder

## Download

Windows installers will be published on the
[Releases page](https://github.com/itourboy-OG/Spicetify-Manager/releases).
Download the newest `Setup.exe`, run it, and keep the desktop-shortcut option
selected. The installer copies every required runtime file, adds Start Menu and
desktop shortcuts, and includes a standard Windows uninstaller.

Windows may show a Microsoft Defender SmartScreen warning for unsigned community
applications. Review the release source and build instructions before running
software you download.

## Run from source

Requirements:

- Windows 10 or Windows 11
- Python 3.10 or newer
- The desktop version of Spotify

Clone or download this repository, then run:

```bat
spicetify.bat
```

The launcher creates a local `.venv` and installs the required interface
dependency automatically.

## Build the portable app

Run:

```bat
build-release.bat
```

The finished application is created in:

```text
dist\Spicetify Manager\
```

Share the entire folder, normally as a ZIP. See
[DISTRIBUTION.md](DISTRIBUTION.md) for the release checklist and update process.

## Build the Windows installer

Install Inno Setup 6, then run:

```bat
build-installer.bat
```

The finished installer is created in:

```text
installer-output\Spicetify-Manager-v2.3.1-Setup.exe
```

The build supports optional Authenticode signing through a certificate installed
in the Windows certificate store. See [CODE_SIGNING.md](CODE_SIGNING.md).

## Important

Spicetify Manager is an independent community project. It is not affiliated
with Spotify or the Spicetify project. Spotify and Spicetify remain separate
third-party applications governed by their own licenses and terms.

## License

Released under the [MIT License](LICENSE).
