# Spicetify Manager v2.4.0 distribution guide

## What can be shared now

Run `build-installer.bat`. The finished Windows installer is created at:

`installer-output\Spicetify-Manager-v2.4.0-Setup.exe`

The installer copies the complete application, creates Start Menu entries,
offers a desktop shortcut by default, and registers a Windows uninstaller.
Recipients do not need Python or PySide6 installed.

For a portable build, run `build-release.bat`. The application is created at:

`dist\Spicetify Manager\Spicetify Manager.exe`

Share the entire `Spicetify Manager` folder, preferably as a ZIP file. The
folder includes the Qt runtime, QML modules, and every required Python runtime
file.

Do not share the portable EXE by itself. It requires the adjacent `_internal`
folder, which is why the installer is the recommended download.

## Enable application update checks

1. Create a GitHub repository for this project.
2. Put its `owner/repository` name in `release_config.json`, for example:

   `"github_repo": "itourboy-OG/Spicetify-Manager"`

3. Run `build-installer.bat` again.
4. On GitHub, create a release tagged with a semantic version such as `v2.4.0`.
5. Upload the new ZIP or installer to that release.

The Settings page will compare the bundled app version with the latest GitHub
Release. When a newer release includes a verified `Setup.exe`, the app can
download it, validate its published size and SHA-256 digest when available, and
launch the installer automatically.

## Recommended public release process

1. Test the portable folder on another Windows account or Windows Sandbox.
2. Zip the complete `dist\Spicetify Manager` folder.
3. Publish the installer on GitHub Releases and optionally include the portable ZIP.
4. Add screenshots and a short explanation that Spotify and Spicetify are
   independent third-party applications.
5. Code-sign the executable before broad public distribution if possible.

Unsigned Windows applications may trigger a Microsoft Defender SmartScreen
warning. Code signing and a stable download location build reputation and make
installation easier for other people.

## Spicetify lifecycle in the app

- **Install Spicetify** downloads the official Windows installation script from
  `github.com/spicetify/cli` and asks before running it.
- **First-time setup** runs `spicetify backup apply`.
- **Remove from Spotify** runs `spicetify restore` and keeps configuration.
- **Fully uninstall Spicetify** restores Spotify, then removes Spicetify's
  per-user program files, configuration, themes, and extensions.

The app detects the supported desktop Spotify installation. Microsoft Store
Spotify is identified separately because Spicetify's official troubleshooting
guidance recommends the desktop version.
