# Changelog

## v2.4.0

Spicetify Manager has been rebuilt with Qt Quick for a smoother, faster, and
more accessible Windows experience.

### Highlights

- New GPU-accelerated Qt Quick interface and navigation
- Searchable Help Center with copyable commands and official documentation
- Guided Spotify detection, first-time setup, repair, restore, and uninstall
- Separate Spicetify CLI and Marketplace update status
- One-click application update checks with verified installer downloads
- Responsive progress percentage that resets after completion
- Searchable activity logs with export, clear, and delete controls
- Configurable notification timer, interface scale, and motion
- Large Text and High Contrast accessibility modes
- Proper Windows installer with desktop and Start Menu shortcuts

### Project cleanup

- Removed the retired CustomTkinter implementation and legacy build scripts
- Consolidated the launcher, PyInstaller specification, and Inno Setup project
- Added current application screenshots and refreshed distribution guidance

The installer is currently unsigned and may trigger a Microsoft Defender
SmartScreen warning.
