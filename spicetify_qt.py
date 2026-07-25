import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime

from PySide6.QtCore import (
    Property,
    QObject,
    QTimer,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine


APP_NAME = "Spicetify Manager"
APP_VERSION = "2.4.0"
APP_PUBLISHER = "SauceBoyz"
SPICETIFY_REPOSITORY = "spicetify/cli"
MARKETPLACE_REPOSITORY = "spicetify/marketplace"
SPICETIFY_INSTALL_SCRIPT = (
    "https://raw.githubusercontent.com/spicetify/cli/main/install.ps1"
)
SPOTIFY_DOWNLOAD_URL = "https://www.spotify.com/download/windows/"
DEFAULT_SETTINGS = {
    "interface_scale": "100%",
    "animations_enabled": True,
    "notification_duration": "3 seconds",
    "always_on_top": False,
    "accessibility_mode": "Standard",
    "_qt_motion_initialized": False,
}
NOTIFICATION_DURATIONS = {
    "2 seconds": 2000,
    "3 seconds": 3000,
    "5 seconds": 5000,
    "8 seconds": 8000,
}


def startup_info():
    if sys.platform == "win32":
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return info
    return None


def strip_ansi(text):
    return re.sub(r"\x1B[@-_][0-?]*[ -/]*[@-~]", "", text)


def version_parts(value):
    value = str(value or "").strip().removeprefix("v")
    match = re.match(r"^(\d+(?:\.\d+)*)", value)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def version_is_newer(candidate, installed):
    candidate_parts = version_parts(candidate)
    installed_parts = version_parts(installed)
    if candidate_parts is None or installed_parts is None:
        return str(candidate) != str(installed)
    width = max(len(candidate_parts), len(installed_parts))
    return candidate_parts + (0,) * (width - len(candidate_parts)) > (
        installed_parts + (0,) * (width - len(installed_parts))
    )


class ManagerBackend(QObject):
    statusChanged = Signal()
    operationChanged = Signal()
    consoleChanged = Signal()
    logsChanged = Signal()
    setupChanged = Signal()
    settingsChanged = Signal()
    appUpdateChanged = Signal()
    toastRequested = Signal(str, str)
    confirmationRequested = Signal(str, str, str)
    errorRequested = Signal(str, str)

    _refreshFinished = Signal(object)
    _setupFinished = Signal(object, object)
    _outputArrived = Signal(str)
    _progressArrived = Signal(float)
    _operationFinished = Signal(str, str, int)
    _downloadFailed = Signal(str, str)
    _marketplaceFilesReady = Signal(object)
    _installerReady = Signal(str)
    _appUpdateResult = Signal(object)
    _appUpdateDownloaded = Signal(str, str)

    def __init__(self, resource_dir):
        super().__init__()
        self.resource_dir = resource_dir
        local_app_data = os.environ.get(
            "LOCALAPPDATA",
            os.path.join(os.path.expanduser("~"), "AppData", "Local"),
        )
        self.data_dir = os.path.join(
            local_app_data, APP_PUBLISHER, "SpicetifyManager"
        )
        self.log_dir = os.path.join(self.data_dir, "logs")
        self.settings_file = os.path.join(self.data_dir, "settings.json")
        self.release_config_file = os.path.join(
            self.resource_dir, "release_config.json"
        )
        os.makedirs(self.data_dir, exist_ok=True)

        self._settings = self._load_settings()
        if not self._settings["_qt_motion_initialized"]:
            # The old Tk animation toggle described a different renderer.
            # Start the approved Qt motion once, then respect future choices.
            self._settings["animations_enabled"] = True
            self._settings["_qt_motion_initialized"] = True
            self._save_settings()
        self._busy = False
        self._cli_title = "Checking Spicetify…"
        self._cli_detail = "Reading the local installation."
        self._marketplace_title = "Checking Marketplace…"
        self._marketplace_detail = "Reading the installed custom app."
        self._marketplace_action_label = "Checking…"
        self._marketplace_action_enabled = False
        self._marketplace_release = None
        self._marketplace_context = None

        self._console_text = "Ready. Choose an action or run a command."
        self._operation_label = "Idle"
        self._operation_state = "idle"
        self._progress = 0.0
        self._progress_visible = False
        self._active_process = None
        self._active_operation = None
        self._operation_callbacks = {}
        self._operation_counter = 0
        self._progress_generation = 0
        self._current_logfile = None
        self._log_lock = threading.Lock()

        self._log_sessions = ["No logs"]
        self._selected_log = "No logs"
        self._full_log_content = ""
        self._log_content = "This session has no activity yet."

        self._spotify_title = "Checking Spotify…"
        self._spotify_detail = "Looking for the desktop installation."
        self._spotify_supported = False
        self._spicetify_setup_title = "Checking Spicetify…"
        self._spicetify_setup_detail = "Looking for the CLI."
        self._spicetify_installed = False

        self._app_update_label = "Check for updates"
        self._app_update_detail = f"{APP_NAME} v{APP_VERSION} is installed."
        self._pending_app_update = None

        self._refreshFinished.connect(self._apply_refresh)
        self._setupFinished.connect(self._apply_setup)
        self._outputArrived.connect(self._append_console)
        self._progressArrived.connect(self._set_progress)
        self._operationFinished.connect(self._finish_operation)
        self._downloadFailed.connect(self._show_download_error)
        self._marketplaceFilesReady.connect(self._configure_marketplace)
        self._installerReady.connect(self._run_downloaded_installer)
        self._appUpdateResult.connect(self._show_app_update_result)
        self._appUpdateDownloaded.connect(self._launch_app_update)

    # ---------- dashboard properties ----------

    @Property(str, notify=statusChanged)
    def cliTitle(self):
        return self._cli_title

    @Property(str, notify=statusChanged)
    def cliDetail(self):
        return self._cli_detail

    @Property(str, notify=statusChanged)
    def marketplaceTitle(self):
        return self._marketplace_title

    @Property(str, notify=statusChanged)
    def marketplaceDetail(self):
        return self._marketplace_detail

    @Property(str, notify=statusChanged)
    def marketplaceActionLabel(self):
        return self._marketplace_action_label

    @Property(bool, notify=statusChanged)
    def marketplaceActionEnabled(self):
        return self._marketplace_action_enabled and not self._busy

    @Property(bool, notify=operationChanged)
    def busy(self):
        return self._busy

    @Property(str, notify=consoleChanged)
    def consoleText(self):
        return self._console_text

    @Property(str, notify=operationChanged)
    def operationLabel(self):
        return self._operation_label

    @Property(str, notify=operationChanged)
    def operationState(self):
        return self._operation_state

    @Property(float, notify=operationChanged)
    def progress(self):
        return self._progress

    @Property(int, notify=operationChanged)
    def progressPercent(self):
        return round(self._progress * 100)

    @Property(bool, notify=operationChanged)
    def progressVisible(self):
        return self._progress_visible

    # ---------- logs properties ----------

    @Property("QStringList", notify=logsChanged)
    def logSessions(self):
        return self._log_sessions

    @Property(str, notify=logsChanged)
    def selectedLog(self):
        return self._selected_log

    @Property(str, notify=logsChanged)
    def logContent(self):
        return self._log_content

    @Property(str, constant=True)
    def logFolder(self):
        return self.log_dir

    # ---------- setup properties ----------

    @Property(str, notify=setupChanged)
    def spotifyTitle(self):
        return self._spotify_title

    @Property(str, notify=setupChanged)
    def spotifyDetail(self):
        return self._spotify_detail

    @Property(bool, notify=setupChanged)
    def spotifySupported(self):
        return self._spotify_supported

    @Property(str, notify=setupChanged)
    def spicetifySetupTitle(self):
        return self._spicetify_setup_title

    @Property(str, notify=setupChanged)
    def spicetifySetupDetail(self):
        return self._spicetify_setup_detail

    @Property(bool, notify=setupChanged)
    def spicetifyInstalled(self):
        return self._spicetify_installed

    # ---------- settings properties ----------

    @Property(bool, notify=settingsChanged)
    def animationsEnabled(self):
        return bool(self._settings["animations_enabled"])

    @Property(bool, notify=settingsChanged)
    def alwaysOnTop(self):
        return bool(self._settings["always_on_top"])

    @Property(str, notify=settingsChanged)
    def notificationDuration(self):
        return self._settings["notification_duration"]

    @Property(int, notify=settingsChanged)
    def notificationDurationMs(self):
        return NOTIFICATION_DURATIONS[self._settings["notification_duration"]]

    @Property(str, notify=settingsChanged)
    def interfaceScale(self):
        return self._settings["interface_scale"]

    @Property(str, notify=settingsChanged)
    def accessibilityMode(self):
        return self._settings["accessibility_mode"]

    @Property(str, notify=appUpdateChanged)
    def appUpdateLabel(self):
        return self._app_update_label

    @Property(str, notify=appUpdateChanged)
    def appUpdateDetail(self):
        return self._app_update_detail

    # ---------- status checks ----------

    @Slot()
    def refreshAll(self):
        if self._busy:
            self._toast("Another operation is already running", "warning")
            return
        self._cli_title = "Checking Spicetify…"
        self._cli_detail = "Reading the local installation."
        self._marketplace_title = "Checking Marketplace…"
        self._marketplace_detail = "Reading the installed custom app."
        self._marketplace_action_label = "Checking…"
        self._marketplace_action_enabled = False
        self.statusChanged.emit()
        threading.Thread(target=self._refresh_worker, daemon=True).start()

    def _refresh_worker(self):
        current_cli = self._spicetify_version()
        cli_release = self._github_release(SPICETIFY_REPOSITORY)
        current_marketplace = self._installed_marketplace_version()
        marketplace_release = self._github_release(MARKETPLACE_REPOSITORY)
        self._refreshFinished.emit(
            {
                "current_cli": current_cli,
                "cli_release": cli_release,
                "current_marketplace": current_marketplace,
                "marketplace_release": marketplace_release,
            }
        )

    @Slot(object)
    def _apply_refresh(self, result):
        current_cli = result["current_cli"]
        cli_release = result["cli_release"]
        latest_cli = self._release_version(cli_release)
        current_marketplace = result["current_marketplace"]
        marketplace_release = result["marketplace_release"]
        latest_marketplace = self._release_version(marketplace_release)
        self._marketplace_release = marketplace_release

        if current_cli:
            if latest_cli and version_is_newer(latest_cli, current_cli):
                self._cli_title = f"Spicetify {latest_cli} is available"
                self._cli_detail = f"Installed version: {current_cli}"
            else:
                self._cli_title = "Spicetify is up to date"
                self._cli_detail = f"Spicetify {current_cli} is ready to use."
                if not latest_cli:
                    self._cli_detail += " Online verification will retry later."
        else:
            self._cli_title = "Spicetify was not found"
            self._cli_detail = "Open Setup & install to install it safely."

        asset = self._marketplace_asset(marketplace_release)
        if not current_marketplace:
            self._marketplace_title = "Marketplace is not installed"
            self._marketplace_detail = (
                f"Marketplace {latest_marketplace} is available."
                if latest_marketplace
                else "The online release check will retry later."
            )
            self._marketplace_action_label = "Install"
            self._marketplace_action_enabled = bool(asset and current_cli)
        elif (
            latest_marketplace
            and current_marketplace != "unknown"
            and version_is_newer(latest_marketplace, current_marketplace)
        ):
            self._marketplace_title = "Marketplace update available"
            self._marketplace_detail = (
                f"Installed {current_marketplace} · Latest {latest_marketplace}"
            )
            self._marketplace_action_label = "Update"
            self._marketplace_action_enabled = bool(asset)
        else:
            self._marketplace_title = "Marketplace is up to date"
            version = (
                current_marketplace
                if current_marketplace != "unknown"
                else "installed"
            )
            self._marketplace_detail = f"Marketplace {version} is ready to use."
            if not latest_marketplace:
                self._marketplace_detail += (
                    " Online verification will retry later."
                )
            self._marketplace_action_label = "Up to date"
            self._marketplace_action_enabled = False
        self.statusChanged.emit()

    # ---------- command execution ----------

    @Slot(str)
    def runAction(self, action):
        commands = {
            "update": ("Updating theme", ["spicetify", "update"]),
            "upgrade": ("Upgrading Spicetify", ["spicetify", "upgrade"]),
            "backup": (
                "Backing up and applying",
                ["spicetify", "backup", "apply"],
            ),
            "restore-confirmed": (
                "Restoring Spotify",
                ["spicetify", "restore"],
            ),
            "first-setup": (
                "Creating backup and applying",
                ["spicetify", "backup", "apply"],
            ),
        }
        if action == "restore":
            self.confirmationRequested.emit(
                "Restore Spotify",
                "Remove Spicetify modifications and return Spotify to its "
                "original state?",
                "restore-confirmed",
            )
            return
        if action in commands:
            label, command = commands[action]
            self._run_operation(label, command)

    @Slot(str)
    def runCustomCommand(self, command):
        command = command.strip()
        if not command:
            self._toast("Enter a command first", "warning")
            return
        self._run_operation(
            "Running custom command",
            command,
            display_command=command,
            use_shell=True,
        )

    def _run_operation(
        self,
        label,
        command,
        display_command=None,
        on_success=None,
        on_failure=None,
        on_finish=None,
        use_shell=False,
    ):
        if self._busy:
            self._toast("Another operation is already running", "warning")
            return
        self._busy = True
        self._active_operation = label
        self._operation_label = label
        self._operation_state = "running"
        self._progress = 0.08
        self._progress_visible = True
        self._progress_generation += 1
        self._operation_counter += 1
        operation_id = str(self._operation_counter)
        self._operation_callbacks[operation_id] = (
            on_success,
            on_failure,
            on_finish,
        )
        self.operationChanged.emit()
        shown = display_command or (
            command
            if isinstance(command, str)
            else subprocess.list2cmdline(command)
        )
        self._write_output(f"\n> {shown}\n")

        def worker():
            return_code = 1
            lines_seen = 0
            try:
                self._active_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=os.path.expanduser("~"),
                    startupinfo=startup_info(),
                    shell=use_shell,
                )
                while True:
                    line = self._active_process.stdout.readline()
                    if line == "" and self._active_process.poll() is not None:
                        break
                    if line:
                        self._write_output(strip_ansi(line))
                        lines_seen += 1
                        self._progressArrived.emit(
                            min(0.88, 0.18 + lines_seen * 0.05)
                        )
                return_code = self._active_process.wait()
            except OSError as error:
                self._write_output(f"Error: {error}\n")
            finally:
                self._active_process = None
                self._operationFinished.emit(
                    operation_id, label, return_code
                )

        threading.Thread(target=worker, daemon=True).start()

    @Slot()
    def cancelOperation(self):
        process = self._active_process
        if process and process.poll() is None:
            process.terminate()
            self._operation_label = "Cancelling…"
            self._operation_state = "warning"
            self.operationChanged.emit()
            self._write_output("\nOperation cancelled by user.\n")

    @Slot(str, str, int)
    def _finish_operation(self, operation_id, label, return_code):
        callbacks = self._operation_callbacks.pop(
            operation_id, (None, None, None)
        )
        on_success, on_failure, on_finish = callbacks
        self._busy = False
        self._active_operation = None
        if return_code == 0:
            self._progress = 1.0
            self._operation_label = "Completed"
            self._operation_state = "success"
            self._write_output(f"{label} completed successfully.\n")
            self._toast(f"{label} completed", "success")
            if on_success:
                try:
                    on_success()
                except Exception as error:
                    self._write_output(
                        f"Post-operation step failed: {error}\n"
                    )
                    self.errorRequested.emit(
                        "Operation incomplete",
                        f"The command completed, but a follow-up step failed:\n{error}",
                    )
            if "Upgrading" in label:
                QTimer.singleShot(250, self.refreshAll)
        else:
            self._progress = 0.0
            self._operation_label = f"Failed · exit code {return_code}"
            self._operation_state = "error"
            self._write_output(
                f"{label} failed with exit code {return_code}.\n"
            )
            self._toast(f"{label} failed", "error")
            if on_failure:
                try:
                    on_failure()
                except Exception as error:
                    self._write_output(f"Rollback failed: {error}\n")
        if on_finish:
            try:
                on_finish()
            except Exception as error:
                self._write_output(f"Cleanup failed: {error}\n")
        self.operationChanged.emit()
        generation = self._progress_generation
        QTimer.singleShot(
            self.notificationDurationMs,
            lambda: self._reset_operation(generation),
        )

    def _reset_operation(self, generation):
        if self._busy or generation != self._progress_generation:
            return
        self._progress_visible = False
        self._progress = 0.0
        self._operation_label = "Idle"
        self._operation_state = "idle"
        self.operationChanged.emit()

    @Slot(float)
    def _set_progress(self, value):
        self._progress = max(0.0, min(1.0, float(value)))
        self.operationChanged.emit()

    def _write_output(self, text):
        logfile = self._ensure_current_logfile()
        with self._log_lock:
            try:
                with open(logfile, "a", encoding="utf-8") as log:
                    log.write(text)
            except OSError:
                pass
        self._outputArrived.emit(text)

    @Slot(str)
    def _append_console(self, text):
        if self._console_text.startswith("Ready."):
            self._console_text = ""
        self._console_text += text
        if len(self._console_text) > 100_000:
            self._console_text = self._console_text[-100_000:]
        self.consoleChanged.emit()

    def _ensure_current_logfile(self):
        if self._current_logfile:
            return self._current_logfile
        os.makedirs(self.log_dir, exist_ok=True)
        self._current_logfile = os.path.join(
            self.log_dir, f"session_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        return self._current_logfile

    # ---------- logs ----------

    @Slot()
    def refreshLogs(self):
        files = []
        for path in glob.glob(os.path.join(self.log_dir, "*.log")):
            try:
                if os.path.getsize(path) > 0:
                    files.append(path)
            except OSError:
                pass
        files.sort(reverse=True)
        self._log_sessions = [
            os.path.basename(path) for path in files
        ] or ["No logs"]
        if self._selected_log not in self._log_sessions:
            self._selected_log = self._log_sessions[0]
        self._load_log_content(self._selected_log, "")

    @Slot(str, str)
    def loadLog(self, selection, search):
        selection = os.path.basename(selection.strip())
        if selection not in self._log_sessions:
            selection = self._log_sessions[0]
        self._selected_log = selection
        self._load_log_content(selection, search)

    def _load_log_content(self, selection, search):
        if not selection or selection == "No logs":
            self._full_log_content = ""
        else:
            path = self._selected_log_path(selection)
            try:
                with open(path, "r", encoding="utf-8") as log:
                    self._full_log_content = log.read()
            except OSError as error:
                self._full_log_content = f"Could not load log: {error}"
        content = self._full_log_content
        term = search.strip().lower()
        if term:
            content = "\n".join(
                line for line in content.splitlines() if term in line.lower()
            )
        self._log_content = (
            content or "This session has no activity yet."
        )
        self.logsChanged.emit()

    @Slot()
    def openLogsFolder(self):
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            os.startfile(self.log_dir)
        except OSError as error:
            self.errorRequested.emit("Open logs folder", str(error))

    @Slot()
    def saveLogCopy(self):
        if not self._full_log_content.strip():
            self._toast("There is no log content to save", "warning")
            return
        destination = os.path.join(
            os.path.expanduser("~"),
            "Desktop",
            f"{os.path.splitext(self._selected_log)[0]}-copy.log",
        )
        try:
            with open(destination, "w", encoding="utf-8") as output:
                output.write(self._full_log_content.rstrip() + "\n")
            self._toast(f"Saved to {destination}", "success")
        except OSError as error:
            self.errorRequested.emit("Save log", str(error))

    @Slot(str)
    def requestLogAction(self, action):
        path = self._selected_log_path(self._selected_log)
        if not path or not os.path.exists(path):
            self._toast("Select a log session first", "warning")
            return
        if action == "delete" and self._current_logfile and (
            os.path.abspath(path) == os.path.abspath(self._current_logfile)
        ):
            self.errorRequested.emit(
                "Active session log",
                "The active session cannot be deleted while the manager is "
                "running. You can clear it now or delete it after restarting.",
            )
            return
        verb = "clear" if action == "clear" else "permanently delete"
        self.confirmationRequested.emit(
            f"{action.title()} selected log",
            f"Do you want to {verb} {os.path.basename(path)}?",
            f"log-{action}",
        )

    def _selected_log_path(self, selection):
        selection = os.path.basename(str(selection or "").strip())
        if not selection or selection == "No logs":
            return None
        root = os.path.abspath(self.log_dir)
        path = os.path.abspath(os.path.join(root, selection))
        if os.path.commonpath((path, root)) != root:
            return None
        return path

    # ---------- setup and repair ----------

    @Slot()
    def refreshSetup(self):
        self._spotify_title = "Checking Spotify…"
        self._spotify_detail = "Looking for the desktop installation."
        self._spicetify_setup_title = "Checking Spicetify…"
        self._spicetify_setup_detail = "Looking for the CLI."
        self.setupChanged.emit()

        def worker():
            spotify = self._detect_spotify()
            spicetify = {
                "version": self._spicetify_version(),
                "path": shutil.which("spicetify.exe")
                or shutil.which("spicetify"),
            }
            self._setupFinished.emit(spotify, spicetify)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object, object)
    def _apply_setup(self, spotify, spicetify):
        self._spotify_supported = bool(spotify["supported"])
        if spotify["supported"]:
            self._spotify_title = "Spotify desktop is ready"
            self._spotify_detail = self._short_path(spotify["path"])
        elif spotify["kind"] == "store":
            self._spotify_title = "Microsoft Store Spotify found"
            self._spotify_detail = (
                "Install desktop Spotify for reliable Spicetify support."
            )
        else:
            self._spotify_title = "Spotify was not found"
            self._spotify_detail = (
                "Install desktop Spotify, then sign in once."
            )

        version = spicetify["version"]
        self._spicetify_installed = bool(version)
        if version:
            self._spicetify_setup_title = (
                f"Spicetify {version} is installed"
            )
            self._spicetify_setup_detail = self._short_path(
                spicetify["path"] or "Available on PATH"
            )
        else:
            self._spicetify_setup_title = "Spicetify is not installed"
            self._spicetify_setup_detail = (
                "Use the official installer below."
            )
        self.setupChanged.emit()

    @Slot(str)
    def setupAction(self, action):
        if action == "spotify":
            QDesktopServices.openUrl(QUrl(SPOTIFY_DOWNLOAD_URL))
        elif action == "install":
            if not self._spotify_supported:
                self.errorRequested.emit(
                    "Spotify desktop required",
                    "Install desktop Spotify and sign in once before "
                    "installing Spicetify.",
                )
                return
            self.confirmationRequested.emit(
                "Install Spicetify",
                "Download and run the official Spicetify Windows installer?",
                "install-spicetify",
            )
        elif action == "first":
            self.runAction("first-setup")
        elif action == "repair":
            self.confirmationRequested.emit(
                "Repair Spicetify",
                "Restore Spotify, create a fresh backup, and reapply "
                "Spicetify? Themes and extensions will be kept.",
                "repair-spicetify",
            )
        elif action == "restore":
            self.runAction("restore")
        elif action == "uninstall":
            self.confirmationRequested.emit(
                "Fully uninstall Spicetify",
                "This restores Spotify and permanently removes Spicetify's "
                "program files, configuration, themes, and extensions for "
                "this Windows account.",
                "uninstall-spicetify",
            )

    @Slot(str)
    def copyHelpCommand(self, command):
        command = str(command or "").strip()
        if not command:
            return
        QGuiApplication.clipboard().setText(command)
        self._toast("Command copied to the clipboard", "success")

    @Slot(str)
    def openHelpLink(self, url):
        url = str(url or "").strip()
        parsed = urllib.parse.urlparse(url)
        hostname = (parsed.hostname or "").lower()
        allowed_domains = ("spicetify.app", "github.com", "spotify.com")
        trusted = (
            parsed.scheme == "https"
            and any(
                hostname == domain or hostname.endswith("." + domain)
                for domain in allowed_domains
            )
        )
        if not trusted:
            self.errorRequested.emit(
                "Link blocked",
                "This Help Center only opens official Spicetify, GitHub, "
                "and Spotify documentation.",
            )
            return
        if not QDesktopServices.openUrl(QUrl(url)):
            self.errorRequested.emit(
                "Could not open link",
                "Windows could not open your default web browser.",
            )

    def _install_spicetify(self):
        if self._busy:
            self._toast("Another operation is already running", "warning")
            return
        self._busy = True
        self._operation_label = "Downloading official installer…"
        self._operation_state = "running"
        self._progress_visible = True
        self._progress = 0.08
        self._progress_generation += 1
        self.operationChanged.emit()

        def worker():
            installer_path = os.path.join(
                self.data_dir, "spicetify-official-install.ps1"
            )
            try:
                request = urllib.request.Request(
                    SPICETIFY_INSTALL_SCRIPT,
                    headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    installer = response.read()
                if len(installer) < 1000 or b"spicetify" not in installer.lower():
                    raise ValueError(
                        "The downloaded installer did not look valid."
                    )
                with open(installer_path, "wb") as installer_file:
                    installer_file.write(installer)
                self._installerReady.emit(installer_path)
            except (OSError, ValueError, urllib.error.URLError) as error:
                self._downloadFailed.emit("Install Spicetify", str(error))

        threading.Thread(target=worker, daemon=True).start()

    def _run_downloaded_installer(self, installer_path):
        self._busy = False
        self._run_operation(
            "Installing Spicetify",
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                installer_path,
            ],
            on_success=self.refreshSetup,
            on_finish=lambda: self._remove_file(installer_path),
        )

    def _repair_spicetify(self):
        if not self._spotify_supported or not self._spicetify_installed:
            self.errorRequested.emit(
                "Repair unavailable",
                "Spotify desktop and Spicetify must both be installed.",
            )
            return
        self._run_operation(
            "Repair 1 of 3 · Restoring Spotify",
            ["spicetify", "restore"],
            on_success=lambda: QTimer.singleShot(
                200,
                lambda: self._run_operation(
                    "Repair 2 of 3 · Creating backup",
                    ["spicetify", "backup"],
                    on_success=lambda: QTimer.singleShot(
                        200,
                        lambda: self._run_operation(
                            "Repair 3 of 3 · Applying Spicetify",
                            ["spicetify", "apply"],
                            on_success=self.refreshSetup,
                        ),
                    ),
                ),
            ),
        )

    def _uninstall_spicetify(self):
        self._run_operation(
            "Restoring before uninstall",
            ["spicetify", "restore"],
            on_success=self._remove_spicetify_files,
        )

    def _remove_spicetify_files(self):
        app_data = os.environ.get("APPDATA", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        targets = [
            os.path.abspath(os.path.join(base, "spicetify"))
            for base in (app_data, local_app_data)
            if base
        ]
        for target in targets:
            parent = os.path.dirname(target)
            if (
                parent
                and os.path.basename(target).lower() == "spicetify"
                and os.path.commonpath((target, parent)) == parent
                and os.path.isdir(target)
            ):
                shutil.rmtree(target)
        self._write_output("Spicetify files and configuration removed.\n")
        self._toast("Spicetify was fully uninstalled", "success")
        QTimer.singleShot(250, self.refreshSetup)

    # ---------- Marketplace ----------

    @Slot()
    def marketplaceAction(self):
        if not self._marketplace_action_enabled:
            self.refreshAll()
            return
        action = (
            "Update"
            if self._installed_marketplace_version()
            else "Install"
        )
        self.confirmationRequested.emit(
            f"{action} Marketplace",
            f"{action} the official Spicetify Marketplace and apply it now?",
            "marketplace-update",
        )

    def _update_marketplace(self):
        release = self._marketplace_release
        asset = self._marketplace_asset(release)
        if not asset:
            self._toast("Checking Marketplace again", "warning")
            self.refreshAll()
            return
        if not self._spicetify_version():
            self.errorRequested.emit(
                "Spicetify required",
                "Install Spicetify before installing Marketplace.",
            )
            return
        if self._busy:
            self._toast("Another operation is already running", "warning")
            return
        self._busy = True
        self._operation_label = "Downloading Marketplace…"
        self._operation_state = "running"
        self._progress_visible = True
        self._progress = 0.08
        self._progress_generation += 1
        self.operationChanged.emit()

        def worker():
            work_dir = tempfile.mkdtemp(
                prefix="marketplace-update-", dir=self.data_dir
            )
            archive_path = os.path.join(work_dir, "marketplace.zip")
            extract_root = os.path.join(work_dir, "extract")
            target = self._marketplace_install_path()
            backup = (
                os.path.join(work_dir, "backup")
                if os.path.isdir(target)
                else None
            )
            context = {
                "work_dir": work_dir,
                "target": target,
                "backup": None,
                "files_replaced": False,
            }
            try:
                self._download_asset(asset, archive_path, 0.72)
                self._safe_extract_zip(archive_path, extract_root)
                source = os.path.join(extract_root, "marketplace-dist")
                if not os.path.isdir(source):
                    candidates = [
                        path
                        for path in glob.glob(
                            os.path.join(extract_root, "**", "marketplace-dist"),
                            recursive=True,
                        )
                        if os.path.isdir(path)
                    ]
                    source = candidates[0] if candidates else ""
                if not source:
                    raise ValueError(
                        "The Marketplace archive did not contain marketplace-dist."
                    )
                if backup:
                    shutil.copytree(target, backup)
                    context["backup"] = backup
                    shutil.rmtree(target)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copytree(source, target)
                context["files_replaced"] = True
                self._marketplaceFilesReady.emit(context)
            except Exception as error:
                self._rollback_marketplace(context)
                self._downloadFailed.emit("Marketplace", str(error))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object)
    def _configure_marketplace(self, context):
        self._marketplace_context = context
        self._busy = False
        self._progress = 0.78
        self._run_operation(
            "Configuring Marketplace",
            ["spicetify", "config", "custom_apps", "marketplace"],
            on_success=lambda: QTimer.singleShot(
                150, self._apply_marketplace
            ),
            on_failure=lambda: self._rollback_marketplace(context),
        )

    def _apply_marketplace(self):
        self._run_operation(
            "Applying Marketplace",
            ["spicetify", "apply"],
            on_success=self._marketplace_complete,
            on_failure=lambda: self._rollback_marketplace(
                self._marketplace_context
            ),
        )

    def _marketplace_complete(self):
        context = self._marketplace_context
        self._marketplace_context = None
        if context:
            shutil.rmtree(context["work_dir"], ignore_errors=True)
        self._toast("Marketplace is ready", "success")
        QTimer.singleShot(250, self.refreshAll)

    @staticmethod
    def _rollback_marketplace(context):
        if not context:
            return
        target = context.get("target")
        backup = context.get("backup")
        try:
            if context.get("files_replaced") and os.path.isdir(target):
                shutil.rmtree(target)
            if backup and os.path.isdir(backup):
                shutil.copytree(backup, target)
        finally:
            shutil.rmtree(context.get("work_dir", ""), ignore_errors=True)

    # ---------- settings and app updates ----------

    @Slot(str, object)
    def setSetting(self, name, value):
        if name not in DEFAULT_SETTINGS:
            return
        if name in {"animations_enabled", "always_on_top"}:
            value = bool(value)
        elif name == "notification_duration":
            if value not in NOTIFICATION_DURATIONS:
                return
        elif name == "interface_scale":
            if value not in {"90%", "100%", "110%"}:
                return
        elif name == "accessibility_mode":
            if value not in {"Standard", "Large text", "High contrast"}:
                return
        self._settings[name] = value
        self._save_settings()
        self.settingsChanged.emit()
        if name in {"interface_scale", "accessibility_mode"}:
            self._toast(
                "Interface appearance updated.",
                "success",
            )
        elif name == "notification_duration":
            self._toast(f"Notifications will stay for {value}", "success")
        elif name == "animations_enabled":
            self._toast(
                "Interface motion enabled"
                if value
                else "Interface motion reduced",
                "success",
            )
        elif name == "always_on_top":
            self._toast(
                "Always on top enabled"
                if value
                else "Always on top disabled",
                "success",
            )

    @Slot()
    def checkAppUpdates(self):
        if self._app_update_label == "Download update":
            release = self._pending_app_update
            self._confirm_app_update(release)
            return
        self._app_update_label = "Checking…"
        self._app_update_detail = "Looking for a newer signed installer."
        self.appUpdateChanged.emit()

        def worker():
            repository = self._configured_repository()
            release = (
                self._github_release(repository) if repository else None
            )
            self._appUpdateResult.emit(release)

        threading.Thread(target=worker, daemon=True).start()

    @Slot(object)
    def _show_app_update_result(self, release):
        latest = self._release_version(release)
        if latest and version_is_newer(latest, APP_VERSION):
            self._pending_app_update = release
            asset = self._app_installer_asset(release)
            self._app_update_label = (
                "Download update" if asset else "View release"
            )
            self._app_update_detail = (
                f"Version {latest} is available."
                if asset
                else f"Version {latest} is available, but no Setup installer was found."
            )
        else:
            self._pending_app_update = None
            self._app_update_label = "Check for updates"
            self._app_update_detail = (
                f"{APP_NAME} v{APP_VERSION} is up to date."
                if latest
                else "The online update check is unavailable. Try again later."
            )
            self._toast(self._app_update_detail, "success" if latest else "warning")
        self.appUpdateChanged.emit()

    def _confirm_app_update(self, release):
        asset = self._app_installer_asset(release)
        latest = self._release_version(release)
        if not asset:
            url = str((release or {}).get("html_url", ""))
            if url:
                QDesktopServices.openUrl(QUrl(url))
            return
        self.confirmationRequested.emit(
            "Application update available",
            f"Download and launch the verified v{latest} installer now?",
            "app-update-download",
        )

    def _download_app_update(self):
        release = self._pending_app_update
        asset = self._app_installer_asset(release)
        latest = self._release_version(release)
        if not asset:
            return
        if self._busy:
            self._toast("Another operation is already running", "warning")
            return
        self._busy = True
        self._operation_label = "Downloading application update…"
        self._operation_state = "running"
        self._progress_visible = True
        self._progress = 0.02
        self._progress_generation += 1
        self.operationChanged.emit()

        def worker():
            try:
                update_dir = os.path.join(self.data_dir, "updates")
                os.makedirs(update_dir, exist_ok=True)
                filename = os.path.basename(
                    str(asset.get("name") or "Spicetify-Manager-Setup.exe")
                )
                path = os.path.join(update_dir, filename)
                self._download_asset(asset, path, 0.96)
                self._appUpdateDownloaded.emit(path, latest)
            except Exception as error:
                self._downloadFailed.emit("Application update", str(error))

        threading.Thread(target=worker, daemon=True).start()

    @Slot(str, str)
    def _launch_app_update(self, installer_path, version):
        try:
            subprocess.Popen(
                [installer_path, "/CLOSEAPPLICATIONS"],
                cwd=os.path.dirname(installer_path),
            )
        except OSError as error:
            self._show_download_error("Application update", str(error))
            return
        self._busy = False
        self._progress = 1.0
        self._operation_label = f"Installer v{version} opened"
        self._operation_state = "success"
        self.operationChanged.emit()
        QTimer.singleShot(600, QGuiApplication.quit)

    @Slot(str)
    def confirmAction(self, action):
        if action == "restore-confirmed":
            self.runAction(action)
        elif action == "install-spicetify":
            self._install_spicetify()
        elif action == "repair-spicetify":
            self._repair_spicetify()
        elif action == "uninstall-spicetify":
            self._uninstall_spicetify()
        elif action == "marketplace-update":
            self._update_marketplace()
        elif action == "app-update-download":
            self._download_app_update()
        elif action in {"log-clear", "log-delete"}:
            path = self._selected_log_path(self._selected_log)
            if not path or not os.path.exists(path):
                return
            try:
                if action == "log-clear":
                    with open(path, "w", encoding="utf-8"):
                        pass
                    self._toast("Selected log cleared", "success")
                else:
                    os.remove(path)
                    self._toast("Selected log deleted", "success")
                self.refreshLogs()
            except OSError as error:
                self.errorRequested.emit("Activity logs", str(error))

    # ---------- infrastructure ----------

    def _load_settings(self):
        settings = dict(DEFAULT_SETTINGS)
        try:
            with open(self.settings_file, "r", encoding="utf-8") as source:
                saved = json.load(source)
            if isinstance(saved, dict):
                for key in settings:
                    if key in saved:
                        settings[key] = saved[key]
        except (OSError, ValueError):
            pass
        if settings["interface_scale"] not in {"90%", "100%", "110%"}:
            settings["interface_scale"] = "100%"
        if settings["notification_duration"] not in NOTIFICATION_DURATIONS:
            settings["notification_duration"] = "3 seconds"
        if settings["accessibility_mode"] not in {
            "Standard",
            "Large text",
            "High contrast",
        }:
            settings["accessibility_mode"] = "Standard"
        settings["animations_enabled"] = bool(
            settings["animations_enabled"]
        )
        settings["always_on_top"] = bool(settings["always_on_top"])
        settings["_qt_motion_initialized"] = bool(
            settings["_qt_motion_initialized"]
        )
        return settings

    def _save_settings(self):
        temporary = self.settings_file + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as output:
                json.dump(self._settings, output, indent=2)
            os.replace(temporary, self.settings_file)
        except OSError:
            self._remove_file(temporary)

    @staticmethod
    def _detect_spotify():
        app_data = os.environ.get("APPDATA", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(app_data, "Spotify", "Spotify.exe"),
            os.path.join(local_app_data, "Spotify", "Spotify.exe"),
        ]
        try:
            import winreg

            for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                try:
                    with winreg.OpenKey(
                        root,
                        r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Spotify.exe",
                    ) as key:
                        candidates.append(winreg.QueryValue(key, None))
                except OSError:
                    pass
        except ImportError:
            pass
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return {
                    "installed": True,
                    "supported": True,
                    "path": os.path.normpath(candidate),
                    "kind": "desktop",
                }
        store_package = os.path.join(
            local_app_data,
            "Packages",
            "SpotifyAB.SpotifyMusic_zpdnekdrzrea0",
        )
        if os.path.isdir(store_package):
            return {
                "installed": True,
                "supported": False,
                "path": store_package,
                "kind": "store",
            }
        return {
            "installed": False,
            "supported": False,
            "path": None,
            "kind": "missing",
        }

    @staticmethod
    def _spicetify_version():
        try:
            result = subprocess.run(
                ["spicetify", "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                startupinfo=startup_info(),
            )
            if result.returncode == 0 and result.stdout.strip():
                return strip_ansi(result.stdout).strip().removeprefix("v")
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    @staticmethod
    def _spicetify_userdata():
        try:
            result = subprocess.run(
                ["spicetify", "path", "userdata"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                startupinfo=startup_info(),
            )
            if result.returncode == 0 and result.stdout.strip():
                return os.path.abspath(
                    strip_ansi(result.stdout).strip().strip('"')
                )
        except (OSError, subprocess.SubprocessError):
            pass
        return os.path.join(
            os.environ.get(
                "APPDATA",
                os.path.join(
                    os.path.expanduser("~"), "AppData", "Roaming"
                ),
            ),
            "spicetify",
        )

    @classmethod
    def _marketplace_install_path(cls):
        return os.path.join(
            cls._spicetify_userdata(), "CustomApps", "marketplace"
        )

    @classmethod
    def _installed_marketplace_version(cls):
        extension_path = os.path.join(
            cls._marketplace_install_path(), "extension.js"
        )
        try:
            with open(
                extension_path, "r", encoding="utf-8", errors="replace"
            ) as source:
                content = source.read(2 * 1024 * 1024)
        except OSError:
            return None
        for pattern in (
            r"Initializing Spicetify Marketplace v([0-9A-Za-z._-]+)",
            r'Marketplace=\{.*?version:"([^"]+)"',
        ):
            match = re.search(pattern, content, flags=re.DOTALL)
            if match:
                return match.group(1).removeprefix("v")
        return "unknown"

    @staticmethod
    def _github_release(repository, timeout=10):
        if not repository:
            return None
        api_url = f"https://api.github.com/repos/{repository}/releases/latest"
        for attempt in range(2):
            try:
                request = urllib.request.Request(
                    api_url,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "Cache-Control": "no-cache",
                        "User-Agent": f"{APP_NAME}/{APP_VERSION}",
                    },
                )
                with urllib.request.urlopen(
                    request, timeout=timeout
                ) as response:
                    release = json.load(response)
                if isinstance(release, dict) and release.get("tag_name"):
                    return release
            except (
                OSError,
                ValueError,
                urllib.error.URLError,
            ):
                if attempt == 0:
                    time.sleep(0.25)
        try:
            request = urllib.request.Request(
                f"https://github.com/{repository}/releases/latest",
                headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"},
            )
            with urllib.request.urlopen(
                request, timeout=timeout
            ) as response:
                final_url = response.geturl()
            match = re.search(r"/releases/tag/([^/?#]+)", final_url)
            if match:
                tag = urllib.parse.unquote(match.group(1))
                return {
                    "tag_name": tag,
                    "html_url": final_url,
                    "assets": [],
                    "_metadata_only": True,
                }
        except (OSError, urllib.error.URLError):
            pass
        return None

    @staticmethod
    def _release_version(release):
        return (
            str((release or {}).get("tag_name", "")).removeprefix("v")
            or None
        )

    @staticmethod
    def _marketplace_asset(release):
        for asset in (release or {}).get("assets", []):
            if str(asset.get("name", "")).lower() == "marketplace.zip":
                return asset
        return None

    @staticmethod
    def _app_installer_asset(release):
        for asset in (release or {}).get("assets", []):
            name = str(asset.get("name", ""))
            if name.lower().endswith("-setup.exe"):
                return asset
        return None

    def _configured_repository(self):
        try:
            with open(
                self.release_config_file, "r", encoding="utf-8"
            ) as source:
                config = json.load(source)
            repository = str(config.get("github_repo", "")).strip()
            if re.fullmatch(r"[^/\s]+/[^/\s]+", repository):
                return repository
        except (OSError, ValueError):
            pass
        return None

    def _download_asset(self, asset, destination, progress_limit):
        url = str(asset.get("browser_download_url", ""))
        if not url:
            raise ValueError("The release download URL was missing.")
        expected_size = int(asset.get("size") or 0)
        expected_digest = str(asset.get("digest") or "")
        digest = hashlib.sha256()
        downloaded = 0
        temporary = destination + ".download"
        request = urllib.request.Request(
            url, headers={"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                with open(temporary, "wb") as output:
                    while True:
                        chunk = response.read(256 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                        digest.update(chunk)
                        downloaded += len(chunk)
                        if expected_size:
                            self._progressArrived.emit(
                                min(
                                    progress_limit,
                                    downloaded
                                    / expected_size
                                    * progress_limit,
                                )
                            )
            if expected_size and downloaded != expected_size:
                raise ValueError(
                    "The downloaded file size did not match the release."
                )
            if expected_digest.lower().startswith("sha256:"):
                expected_hash = expected_digest.split(":", 1)[1].lower()
                if digest.hexdigest().lower() != expected_hash:
                    raise ValueError(
                        "The downloaded file checksum did not match."
                    )
            os.replace(temporary, destination)
        finally:
            self._remove_file(temporary)

    @staticmethod
    def _safe_extract_zip(archive_path, destination):
        root = os.path.abspath(destination)
        os.makedirs(root, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                target = os.path.abspath(os.path.join(root, member.filename))
                if os.path.commonpath((root, target)) != root:
                    raise ValueError(
                        "The archive contained an unsafe file path."
                    )
            archive.extractall(root)

    @staticmethod
    def _short_path(path, max_length=72):
        path = str(path or "")
        return (
            path
            if len(path) <= max_length
            else "…" + path[-(max_length - 1) :]
        )

    @staticmethod
    def _remove_file(path):
        try:
            if path and os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass

    @Slot(str, str)
    def _show_download_error(self, title, message):
        self._busy = False
        self._progress = 0.0
        self._progress_visible = False
        self._operation_label = "Failed"
        self._operation_state = "error"
        self.operationChanged.emit()
        self.errorRequested.emit(title, message)

    def _toast(self, text, kind="success"):
        self.toastRequested.emit(str(text), kind)


def main():
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    app = QGuiApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_PUBLISHER)

    resource_dir = getattr(
        sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
    )
    icon_path = os.path.join(resource_dir, "icon.ico")
    app.setWindowIcon(QIcon(icon_path))

    backend = ManagerBackend(resource_dir)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("backend", backend)
    engine.rootContext().setContextProperty(
        "appIconUrl", QUrl.fromLocalFile(icon_path)
    )
    engine.rootContext().setContextProperty("appVersion", APP_VERSION)
    engine.load(
        QUrl.fromLocalFile(os.path.join(resource_dir, "qml", "Main.qml"))
    )
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    window.setFlag(Qt.WindowStaysOnTopHint, backend.alwaysOnTop)
    backend.settingsChanged.connect(
        lambda: window.setFlag(
            Qt.WindowStaysOnTopHint, backend.alwaysOnTop
        )
    )
    QTimer.singleShot(100, backend.refreshAll)
    QTimer.singleShot(180, backend.refreshSetup)
    QTimer.singleShot(220, backend.refreshLogs)
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(1800, app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
