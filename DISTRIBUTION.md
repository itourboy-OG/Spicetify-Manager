# Spicetify Manager v2.1.0 distribution guide

## What can be shared now

Run `build-release.bat`. The finished portable application is created at:

`dist\Spicetify Manager\Spicetify Manager.exe`

Share the entire `Spicetify Manager` folder, preferably as a ZIP file. The
official CustomTkinter packaging guidance uses a folder-based build because the
UI library includes required fonts and theme data.

Recipients do not need Python or CustomTkinter installed.

## Enable application update checks

1. Create a GitHub repository for this project.
2. Put its `owner/repository` name in `release_config.json`, for example:

   `"github_repo": "itourboy-OG/Spicetify-Manager"`

3. Run `build-release.bat` again.
4. On GitHub, create a release tagged with a semantic version such as `v2.1.0`.
5. Upload the new ZIP or installer to that release.

The Settings page will compare the bundled app version with the latest GitHub
Release. When a newer release exists, it offers to open the official release
page for downloading.

## Recommended public release process

1. Test the portable folder on another Windows account or Windows Sandbox.
2. Zip the complete `dist\Spicetify Manager` folder.
3. Publish the ZIP on GitHub Releases.
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
