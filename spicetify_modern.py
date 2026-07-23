import getpass
import glob
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from packaging.version import InvalidVersion, Version
from PIL import Image


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class SpicetifyManager(ctk.CTk):
    APP_NAME = "Spicetify Manager"
    APP_VERSION = "2.2.0"
    APP_VERSION_FULL = "2.2.0"
    UI_FONT = "Verdana"
    MONO_FONT = "Consolas"
    PROGRESS_WIDTH = 220
    SPICETIFY_INSTALL_SCRIPT = (
        "https://raw.githubusercontent.com/spicetify/cli/main/install.ps1"
    )
    SPOTIFY_DOWNLOAD_URL = "https://www.spotify.com/download/windows/"
    BG = "#090D18"
    SIDEBAR = "#0D1322"
    CARD = "#111A2D"
    CARD_HOVER = "#16223A"
    BORDER = "#22314F"
    TEXT = "#F2F6FF"
    MUTED = "#8C9AB5"
    BLUE = "#5B8CFF"
    BLUE_HOVER = "#76A0FF"
    GREEN = "#1ED760"
    GREEN_HOVER = "#33E477"
    ORANGE = "#FFB454"
    RED = "#FF647C"
    DEFAULT_SETTINGS = {
        "interface_scale": "100%",
        "animations_enabled": True,
        "notification_duration": "3 seconds",
        "always_on_top": False,
    }
    NOTIFICATION_DURATIONS = {
        "2 seconds": 2000,
        "3 seconds": 3000,
        "5 seconds": 5000,
        "8 seconds": 8000,
    }

    NAV_ITEMS = (
        ("dashboard", "⌂", "Dashboard"),
        ("logs", "≡", "Activity logs"),
        ("help", "?", "Help center"),
        ("setup", "✦", "Setup & install"),
        ("settings", "⚙", "Settings"),
    )

    def __init__(self, preview_update=False):
        super().__init__()
        self.title("SauceBoyz · Spicetify Manager")
        self.geometry("1180x760")
        self.minsize(1000, 680)
        self.configure(fg_color=self.BG)

        self.resource_dir = getattr(
            sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
        )
        local_app_data = os.environ.get(
            "LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local")
        )
        self.data_dir = os.path.join(
            local_app_data, "SauceBoyz", "SpicetifyManager"
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self.settings_file = os.path.join(self.data_dir, "settings.json")
        self.release_config_file = os.path.join(
            self.resource_dir, "release_config.json"
        )
        self._migrate_legacy_settings()
        self.settings = self._load_settings()
        self.animations_enabled = bool(self.settings["animations_enabled"])
        self.notification_duration_ms = self.NOTIFICATION_DURATIONS.get(
            self.settings["notification_duration"], 3000
        )
        ctk.set_widget_scaling(
            int(self.settings["interface_scale"].rstrip("%")) / 100
        )
        self.attributes("-topmost", bool(self.settings["always_on_top"]))
        try:
            self.iconbitmap(os.path.join(self.resource_dir, "icon.ico"))
        except OSError:
            pass

        self.log_dir = os.path.join(self.data_dir, "logs")
        self.current_logfile = None

        self.ui_queue = queue.Queue()
        self.log_lock = threading.Lock()
        self.active_process = None
        self.active_operation = None
        self.current_page = None
        self.nav_indicator_y = 132
        self.spinner_job = None
        self.spinner_frame = 0
        self.progress_value = 0.0
        self.progress_animation_generation = 0
        self.page_animation_generation = 0
        self.nav_animation_generation = 0
        self.progress_collapse_generation = 0
        self.status_reset_job = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_workspace()
        self._build_pages()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(40, self._drain_ui_queue)
        self.show_page("dashboard", animate=False)
        if preview_update:
            self.after(
                250,
                lambda: self._show_version_result("2.44.0", "2.45.0"),
            )
        else:
            self.check_for_updates()

    # ---------- layout ----------

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=224, corner_radius=0, fg_color=self.SIDEBAR
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        icon_path = os.path.join(self.resource_dir, "icon.ico")
        with Image.open(icon_path) as icon_source:
            brand_icon = icon_source.convert("RGBA")
        self.sidebar_logo_image = ctk.CTkImage(
            light_image=brand_icon,
            dark_image=brand_icon,
            size=(42, 42),
        )
        self.sidebar_identity_image = ctk.CTkImage(
            light_image=brand_icon,
            dark_image=brand_icon,
            size=(34, 34),
        )
        ctk.CTkLabel(
            self.sidebar,
            text="",
            image=self.sidebar_logo_image,
            width=42,
            height=42,
        ).place(x=22, y=24)
        ctk.CTkLabel(
            self.sidebar,
            text="SauceBoyz",
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 19, "bold"),
        ).place(x=76, y=26)
        ctk.CTkLabel(
            self.sidebar,
            text="SPICETIFY MANAGER",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 11, "bold"),
        ).place(x=77, y=49)

        self.nav_indicator = ctk.CTkFrame(
            self.sidebar,
            width=4,
            height=40,
            corner_radius=4,
            fg_color=self.GREEN,
        )
        self.nav_indicator.place(x=0, y=self.nav_indicator_y)

        self.nav_buttons = {}
        for index, (key, icon, label) in enumerate(self.NAV_ITEMS):
            y = 126 + index * 54
            button = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}    {label}",
                anchor="w",
                width=190,
                height=46,
                corner_radius=11,
                border_width=0,
                fg_color="transparent",
                hover_color=self.CARD_HOVER,
                text_color=self.MUTED,
                font=ctk.CTkFont(self.UI_FONT, 13, "bold"),
                command=lambda page=key: self.show_page(page),
            )
            button.place(x=16, y=y)
            self.nav_buttons[key] = (button, y + 6)

        self.sidebar_identity = ctk.CTkFrame(
            self.sidebar,
            width=184,
            height=88,
            corner_radius=14,
            fg_color=self.CARD,
            border_width=1,
            border_color=self.BORDER,
        )
        self.sidebar_identity.place(x=20, rely=1.0, y=-112)
        ctk.CTkLabel(
            self.sidebar_identity,
            text="",
            image=self.sidebar_identity_image,
            width=34,
            height=34,
        ).place(x=14, y=26)
        ctk.CTkLabel(
            self.sidebar_identity,
            text=self.APP_NAME,
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 12, "bold"),
        ).place(x=57, y=25)
        ctk.CTkLabel(
            self.sidebar_identity,
            text=f"Version v{self.APP_VERSION}",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 12),
        ).place(x=57, y=50)

    def _build_workspace(self):
        self.workspace = ctk.CTkFrame(self, fg_color=self.BG, corner_radius=0)
        self.workspace.grid(row=0, column=1, sticky="nsew")
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(1, weight=1)

        self.topbar = ctk.CTkFrame(
            self.workspace, height=92, fg_color=self.BG, corner_radius=0
        )
        self.topbar.grid(row=0, column=0, sticky="ew", padx=34)
        self.topbar.grid_propagate(False)
        self.topbar.grid_columnconfigure(0, weight=1)

        self.page_title = ctk.CTkLabel(
            self.topbar,
            text="Dashboard",
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 28, "bold"),
        )
        self.page_title.grid(row=0, column=0, sticky="sw", pady=(22, 0))
        self.page_subtitle = ctk.CTkLabel(
            self.topbar,
            text="Everything you need to keep Spicetify healthy.",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 12),
        )
        self.page_subtitle.grid(row=1, column=0, sticky="nw")

        self.top_status = ctk.CTkLabel(
            self.topbar,
            text="  ●  Ready  ",
            height=34,
            corner_radius=17,
            fg_color=self.CARD,
            text_color=self.GREEN,
            font=ctk.CTkFont(self.UI_FONT, 12, "bold"),
        )
        self.top_status.grid(row=0, column=1, rowspan=2, sticky="e", pady=(22, 0))

        self.page_host = ctk.CTkFrame(
            self.workspace, fg_color=self.BG, corner_radius=0
        )
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=34, pady=(4, 28))

    def _build_pages(self):
        self.pages = {}
        self.pages["dashboard"] = self._create_dashboard()
        self.pages["logs"] = self._create_logs_page()
        self.pages["help"] = self._create_help_page()
        self.pages["setup"] = self._create_setup_page()
        self.pages["settings"] = self._create_settings_page()

    def _base_page(self):
        return ctk.CTkFrame(self.page_host, fg_color=self.BG, corner_radius=0)

    def _create_dashboard(self):
        page = self._base_page()
        page.grid_columnconfigure((0, 1), weight=1, uniform="dashboard")
        page.grid_rowconfigure(3, weight=1)

        hero = ctk.CTkFrame(
            page,
            height=138,
            corner_radius=20,
            fg_color=self.CARD,
            border_width=1,
            border_color=self.BORDER,
        )
        hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        hero.grid_propagate(False)
        hero.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hero,
            text="SPICETIFY STATUS",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 11, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(20, 0))
        self.hero_title = ctk.CTkLabel(
            hero,
            text="Checking your installation…",
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 23, "bold"),
        )
        self.hero_title.grid(row=1, column=0, sticky="w", padx=24, pady=(3, 0))
        self.hero_detail = ctk.CTkLabel(
            hero,
            text="This only takes a moment.",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 12),
        )
        self.hero_detail.grid(row=2, column=0, sticky="w", padx=24, pady=(2, 18))
        self.check_button = ctk.CTkButton(
            hero,
            text="Check again",
            width=122,
            height=38,
            corner_radius=12,
            fg_color=self.CARD_HOVER,
            hover_color=self.BORDER,
            border_width=1,
            border_color=self.BORDER,
            font=ctk.CTkFont(self.UI_FONT, 12, "bold"),
            command=self.check_for_updates,
        )
        self.check_button.grid(row=0, column=1, rowspan=3, padx=24)

        actions = (
            ("Update theme", "Hot-reload active theme changes", self.BLUE, self.run_update),
            ("Upgrade CLI", "Install the newest Spicetify release", self.GREEN, self.run_upgrade),
            ("Backup & apply", "Reapply after a Spotify update", "#9B7BFF", self.run_backup_apply),
            ("Restore Spotify", "Return Spotify to its original state", self.ORANGE, self.run_restore),
        )
        for index, (title, detail, color, command) in enumerate(actions):
            card = self._action_card(page, title, detail, color, command)
            card.grid(
                row=1,
                column=index % 2,
                sticky="ew",
                padx=(0, 8) if index % 2 == 0 else (8, 0),
                pady=(0, 16) if index < 2 else 0,
            )
            if index >= 2:
                card.grid_configure(row=2)

        console_card = ctk.CTkFrame(
            page,
            corner_radius=20,
            fg_color=self.CARD,
            border_width=1,
            border_color=self.BORDER,
        )
        console_card.grid(
            row=3, column=0, columnspan=2, sticky="nsew", pady=(16, 0)
        )
        console_card.grid_columnconfigure(0, weight=1)
        console_card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            console_card,
            text="Command console",
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 15, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(15, 8))

        controls = ctk.CTkFrame(console_card, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        controls.grid_columnconfigure(0, weight=1)
        self.command_entry = ctk.CTkEntry(
            controls,
            height=38,
            corner_radius=11,
            border_width=1,
            border_color=self.BORDER,
            fg_color=self.BG,
            placeholder_text="Enter a command, for example: spicetify config",
            font=ctk.CTkFont(self.MONO_FONT, 12),
        )
        self.command_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.command_entry.bind("<Return>", lambda _event: self.run_custom_command())
        self.run_button = ctk.CTkButton(
            controls,
            text="Run",
            width=78,
            height=38,
            corner_radius=11,
            fg_color=self.BLUE,
            hover_color=self.BLUE_HOVER,
            font=ctk.CTkFont(self.UI_FONT, 12, "bold"),
            command=self.run_custom_command,
        )
        self.run_button.grid(row=0, column=1, padx=4)
        self.cancel_button = ctk.CTkButton(
            controls,
            text="Cancel",
            width=78,
            height=38,
            corner_radius=11,
            fg_color="transparent",
            hover_color="#3A1E2A",
            border_width=1,
            border_color=self.BORDER,
            text_color=self.MUTED,
            state="disabled",
            command=self.cancel_operation,
        )
        self.cancel_button.grid(row=0, column=2, padx=(4, 0))

        self.console = ctk.CTkTextbox(
            console_card,
            height=160,
            corner_radius=12,
            border_width=0,
            fg_color="#080C15",
            text_color="#C8D4EA",
            font=ctk.CTkFont(self.MONO_FONT, 12),
            wrap="word",
        )
        self.console.grid(row=2, column=0, sticky="nsew", padx=18)
        self.console.insert("end", "Ready. Choose an action or run a command.\n")
        self.console.configure(state="disabled")

        footer = ctk.CTkFrame(console_card, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=18, pady=12)
        footer.grid_columnconfigure(0, weight=1)
        self.operation_label = ctk.CTkLabel(
            footer,
            text="Idle",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 12),
        )
        self.operation_label.grid(row=0, column=0, sticky="w")
        self.progress = ctk.CTkProgressBar(
            footer,
            width=220,
            height=8,
            corner_radius=8,
            fg_color=self.BORDER,
            progress_color=self.GREEN,
        )
        self.progress.grid(row=0, column=1, sticky="e")
        self.progress.set(0)
        self.progress_percent = ctk.CTkLabel(
            footer,
            text="0%",
            width=42,
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 12, "bold"),
        )
        self.progress_percent.grid(row=0, column=2, sticky="e", padx=(10, 0))
        self.progress.grid_remove()
        self.progress_percent.grid_remove()
        return page

    def _action_card(self, parent, title, detail, accent, command):
        card = ctk.CTkFrame(
            parent,
            height=84,
            corner_radius=18,
            fg_color=self.CARD,
            border_width=1,
            border_color=self.BORDER,
        )
        card.grid_propagate(False)
        card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            card,
            text="●",
            width=34,
            text_color=accent,
            font=ctk.CTkFont(size=21),
        ).grid(row=0, column=0, rowspan=2, padx=(17, 7))
        ctk.CTkLabel(
            card,
            text=title,
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 13, "bold"),
        ).grid(row=0, column=1, sticky="sw", pady=(16, 0))
        ctk.CTkLabel(
            card,
            text=detail,
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 11),
        ).grid(row=1, column=1, sticky="nw", pady=(0, 15))
        ctk.CTkButton(
            card,
            text="→",
            width=38,
            height=38,
            corner_radius=12,
            fg_color=self.CARD_HOVER,
            hover_color=accent,
            border_width=1,
            border_color=self.BORDER,
            font=ctk.CTkFont(size=18, weight="bold"),
            command=command,
        ).grid(row=0, column=2, rowspan=2, padx=18)
        return card

    def _create_logs_page(self):
        page = self._base_page()
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(
            page,
            corner_radius=16,
            fg_color=self.CARD,
            border_width=1,
            border_color=self.BORDER,
        )
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        toolbar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            toolbar,
            text="Session",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 12, "bold"),
        ).grid(row=0, column=0, padx=(18, 8), pady=14)
        self.log_session = ctk.CTkComboBox(
            toolbar,
            values=["No logs"],
            height=36,
            corner_radius=10,
            border_color=self.BORDER,
            fg_color=self.BG,
            button_color=self.BORDER,
            command=self.load_log_session,
        )
        self.log_session.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=12)
        self.log_search = ctk.CTkEntry(
            toolbar,
            width=210,
            height=36,
            corner_radius=10,
            border_color=self.BORDER,
            fg_color=self.BG,
            placeholder_text="Search this log",
        )
        self.log_search.grid(row=0, column=2, padx=6)
        self.log_search.bind("<KeyRelease>", lambda _event: self.filter_log())
        ctk.CTkButton(
            toolbar,
            text="Refresh",
            width=84,
            height=36,
            corner_radius=10,
            fg_color=self.BLUE,
            hover_color=self.BLUE_HOVER,
            command=self.refresh_logs,
        ).grid(row=0, column=3, padx=(6, 16))

        self.logs_text = ctk.CTkTextbox(
            page,
            corner_radius=18,
            border_width=1,
            border_color=self.BORDER,
            fg_color=self.CARD,
            text_color="#CAD7EE",
            font=ctk.CTkFont(self.MONO_FONT, 12),
            wrap="word",
        )
        self.logs_text.grid(row=1, column=0, sticky="nsew")
        self.full_log_content = ""

        footer = ctk.CTkFrame(page, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        ctk.CTkButton(
            footer,
            text="Save a copy",
            width=110,
            height=36,
            corner_radius=10,
            fg_color=self.CARD,
            hover_color=self.CARD_HOVER,
            border_width=1,
            border_color=self.BORDER,
            command=self.save_log_copy,
        ).pack(side="left")
        ctk.CTkButton(
            footer,
            text="Open logs folder",
            width=132,
            height=36,
            corner_radius=10,
            fg_color=self.CARD,
            hover_color=self.CARD_HOVER,
            border_width=1,
            border_color=self.BORDER,
            command=self.open_logs_folder,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            footer,
            text="Clear selected",
            width=118,
            height=36,
            corner_radius=10,
            fg_color=self.CARD,
            hover_color="#4A3420",
            border_width=1,
            border_color=self.ORANGE,
            text_color=self.ORANGE,
            command=self.clear_selected_log,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            footer,
            text="Delete selected",
            width=124,
            height=36,
            corner_radius=10,
            fg_color=self.CARD,
            hover_color="#481F2A",
            border_width=1,
            border_color=self.RED,
            text_color=self.RED,
            command=self.delete_selected_log,
        ).pack(side="right")
        self.refresh_logs()
        return page

    def _create_help_page(self):
        page = self._base_page()
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        text = ctk.CTkTextbox(
            page,
            corner_radius=20,
            border_width=1,
            border_color=self.BORDER,
            fg_color=self.CARD,
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 13),
            wrap="word",
            padx=24,
            pady=20,
        )
        text.grid(row=0, column=0, sticky="nsew")
        text.insert(
            "end",
            """Quick guide

UPDATE THEME
Hot-reloads changes to your active Spicetify theme.

UPGRADE CLI
Updates script-based Spicetify installations to the latest release.

BACKUP & APPLY
Rebuilds Spotify's backup and reapplies your customizations. This is the usual
action after Spotify updates itself.

RESTORE SPOTIFY
Removes Spicetify modifications and restores Spotify to its original state.
Your Spicetify configuration and customization files are preserved.

COMMAND CONSOLE
Run any Spicetify command and watch its output in real time. Use Cancel to stop
a long-running process.

Useful commands
  spicetify config
  spicetify config current_theme
  spicetify apply
  spicetify path
  spicetify --help

Official documentation
  https://spicetify.app/docs
""",
        )
        text.configure(state="disabled")
        return page

    def _create_setup_page(self):
        page = self._base_page()
        page.grid_columnconfigure(0, weight=1)

        overview = ctk.CTkFrame(
            page,
            height=118,
            corner_radius=20,
            fg_color=self.CARD,
            border_width=1,
            border_color=self.BORDER,
        )
        overview.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        overview.grid_propagate(False)
        overview.grid_columnconfigure((0, 1), weight=1, uniform="system")
        ctk.CTkLabel(
            overview,
            text="SYSTEM CHECK",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(15, 3))
        self.spotify_setup_status = ctk.CTkLabel(
            overview,
            text="◐  Checking Spotify…",
            text_color=self.ORANGE,
            font=ctk.CTkFont(self.UI_FONT, 14, "bold"),
        )
        self.spotify_setup_status.grid(row=1, column=0, sticky="w", padx=20)
        self.spicetify_setup_status = ctk.CTkLabel(
            overview,
            text="◐  Checking Spicetify…",
            text_color=self.ORANGE,
            font=ctk.CTkFont(self.UI_FONT, 14, "bold"),
        )
        self.spicetify_setup_status.grid(row=1, column=1, sticky="w", padx=20)
        self.spotify_setup_detail = ctk.CTkLabel(
            overview,
            text="Looking for the desktop application",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 11),
        )
        self.spotify_setup_detail.grid(row=2, column=0, sticky="w", padx=20)
        self.spicetify_setup_detail = ctk.CTkLabel(
            overview,
            text="Looking for the command-line tool",
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 11),
        )
        self.spicetify_setup_detail.grid(row=2, column=1, sticky="w", padx=20)

        install = self._setup_action_card(
            page,
            1,
            "Install Spicetify",
            "Downloads and runs the official Spicetify Windows installer.",
            self.GREEN,
            "Install",
            self.install_spicetify,
        )
        self.install_spicetify_button = install

        spotify = self._setup_action_card(
            page,
            2,
            "Get desktop Spotify",
            "Opens Spotify's official Windows download page if Spotify is missing.",
            self.BLUE,
            "Download",
            lambda: webbrowser.open(self.SPOTIFY_DOWNLOAD_URL),
        )
        self.download_spotify_button = spotify

        first_setup = self._setup_action_card(
            page,
            3,
            "First-time setup",
            "Creates a clean backup and applies Spicetify to Spotify.",
            "#9B7BFF",
            "Backup & apply",
            self.run_backup_apply,
        )
        self.first_setup_button = first_setup

        restore = self._setup_action_card(
            page,
            4,
            "Remove from Spotify",
            "Restores vanilla Spotify but keeps Spicetify and your configuration.",
            self.ORANGE,
            "Restore",
            self.run_restore,
        )
        self.remove_modifications_button = restore

        uninstall = self._setup_action_card(
            page,
            5,
            "Fully uninstall Spicetify",
            "Restores Spotify, then removes Spicetify's files and configuration.",
            self.RED,
            "Uninstall",
            self.uninstall_spicetify,
        )
        self.full_uninstall_button = uninstall

        self.after(100, self.refresh_system_detection)
        return page

    def _setup_action_card(
        self, parent, row, title, detail, accent, button_text, command
    ):
        card = ctk.CTkFrame(
            parent,
            height=74,
            corner_radius=17,
            fg_color=self.CARD,
            border_width=1,
            border_color=self.BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", pady=(0, 11))
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 13, "bold"),
        ).grid(row=0, column=0, sticky="sw", padx=20, pady=(12, 0))
        ctk.CTkLabel(
            card,
            text=detail,
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 11),
        ).grid(row=1, column=0, sticky="nw", padx=20, pady=(0, 11))
        button = ctk.CTkButton(
            card,
            text=button_text,
            width=120,
            height=36,
            corner_radius=10,
            fg_color=self.CARD_HOVER,
            hover_color=accent,
            border_width=1,
            border_color=accent,
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 12, "bold"),
            command=command,
        )
        button.grid(row=0, column=1, rowspan=2, padx=18)
        return button

    def _create_settings_page(self):
        page = self._base_page()
        page.grid_columnconfigure(0, weight=1)

        appearance = self._settings_card(
            page,
            "Interface scale",
            "Adjust the size of controls and text without changing Windows settings.",
        )
        appearance.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        self.theme_menu = ctk.CTkOptionMenu(
            appearance,
            values=["90%", "100%", "110%"],
            width=130,
            height=38,
            corner_radius=10,
            fg_color=self.BLUE,
            button_color=self.BLUE_HOVER,
            command=self.change_scale,
        )
        self.theme_menu.set(self.settings["interface_scale"])
        self.theme_menu.grid(row=0, column=1, rowspan=2, padx=20)

        motion = self._settings_card(
            page,
            "Interface motion",
            "Smooth page transitions, progress movement, and status feedback.",
        )
        motion.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        self.motion_switch = ctk.CTkSwitch(
            motion,
            text="",
            width=48,
            progress_color=self.GREEN,
            command=self.toggle_animations,
        )
        if self.animations_enabled:
            self.motion_switch.select()
        else:
            self.motion_switch.deselect()
        self.motion_switch.grid(row=0, column=1, rowspan=2, padx=20)

        notifications = self._settings_card(
            page,
            "Notification duration",
            "Choose how long notifications and completion status remain visible.",
        )
        notifications.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        self.notification_menu = ctk.CTkOptionMenu(
            notifications,
            values=list(self.NOTIFICATION_DURATIONS),
            width=130,
            height=38,
            corner_radius=10,
            fg_color=self.BLUE,
            button_color=self.BLUE_HOVER,
            command=self.change_notification_duration,
        )
        self.notification_menu.set(self.settings["notification_duration"])
        self.notification_menu.grid(row=0, column=1, rowspan=2, padx=20)

        always_on_top = self._settings_card(
            page,
            "Always on top",
            "Keep the manager above other windows while commands are running.",
        )
        always_on_top.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        self.always_on_top_switch = ctk.CTkSwitch(
            always_on_top,
            text="",
            width=48,
            progress_color=self.GREEN,
            command=self.toggle_always_on_top,
        )
        if self.settings["always_on_top"]:
            self.always_on_top_switch.select()
        else:
            self.always_on_top_switch.deselect()
        self.always_on_top_switch.grid(row=0, column=1, rowspan=2, padx=20)

        storage = self._settings_card(
            page,
            "Activity storage",
            f"Session logs are stored in {self.log_dir}",
        )
        storage.grid(row=4, column=0, sticky="ew")
        ctk.CTkButton(
            storage,
            text="Open folder",
            width=110,
            height=38,
            corner_radius=10,
            fg_color=self.CARD_HOVER,
            hover_color=self.BORDER,
            border_width=1,
            border_color=self.BORDER,
            command=self.open_logs_folder,
        ).grid(row=0, column=1, rowspan=2, padx=20)

        app_updates = self._settings_card(
            page,
            "Application updates",
            f"{self.APP_NAME} v{self.APP_VERSION} · checks your configured GitHub Releases feed.",
        )
        app_updates.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        self.app_update_button = ctk.CTkButton(
            app_updates,
            text="Check now",
            width=110,
            height=38,
            corner_radius=10,
            fg_color=self.CARD_HOVER,
            hover_color=self.BLUE,
            border_width=1,
            border_color=self.BLUE,
            command=self.check_app_updates,
        )
        self.app_update_button.grid(row=0, column=1, rowspan=2, padx=20)
        return page

    def _settings_card(self, parent, title, detail):
        card = ctk.CTkFrame(
            parent,
            height=78,
            corner_radius=18,
            fg_color=self.CARD,
            border_width=1,
            border_color=self.BORDER,
        )
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=title,
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 14, "bold"),
        ).grid(row=0, column=0, sticky="sw", padx=20, pady=(17, 0))
        ctk.CTkLabel(
            card,
            text=detail,
            text_color=self.MUTED,
            font=ctk.CTkFont(self.UI_FONT, 12),
        ).grid(row=1, column=0, sticky="nw", padx=20, pady=(1, 10))
        return card

    # ---------- navigation and animation ----------

    def show_page(self, page_name, animate=True):
        if page_name == self.current_page:
            return
        titles = {
            "dashboard": ("Dashboard", "Everything you need to keep Spicetify healthy."),
            "logs": ("Activity logs", "Search, review, and export command history."),
            "help": ("Help center", "A quick reference for the actions in this manager."),
            "setup": (
                "Setup & install",
                "Prepare Spotify, install Spicetify, or remove it safely.",
            ),
            "settings": ("Settings", "Make the manager work the way you prefer."),
        }
        old_page = self.pages.get(self.current_page)
        new_page = self.pages[page_name]
        self.page_animation_generation += 1
        transition_generation = self.page_animation_generation
        if old_page:
            old_page.place_forget()

        target_y = self.nav_buttons[page_name][1]
        self._animate_indicator(target_y)
        for key, (button, _y) in self.nav_buttons.items():
            selected = key == page_name
            button.configure(
                fg_color=self.CARD if selected else "transparent",
                text_color=self.TEXT if selected else self.MUTED,
            )

        title, subtitle = titles[page_name]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        self.current_page = page_name

        if animate and self.animations_enabled:
            new_page.place(x=14, y=0, relwidth=1, relheight=1)
            self._slide_page(new_page, 14, transition_generation)
        else:
            new_page.place(x=0, y=0, relwidth=1, relheight=1)
        if page_name == "logs":
            self.refresh_logs()
        elif page_name == "setup":
            self.refresh_system_detection()

    def _slide_page(self, page, x, generation):
        if (
            generation != self.page_animation_generation
            or not page.winfo_exists()
            or page != self.pages.get(self.current_page)
        ):
            return
        next_x = max(0, int(x * 0.52) - 1)
        page.place_configure(x=next_x)
        if next_x > 0:
            self.after(
                16, lambda: self._slide_page(page, next_x, generation)
            )

    def _animate_indicator(self, target):
        self.nav_animation_generation += 1
        generation = self.nav_animation_generation
        if not self.animations_enabled:
            self.nav_indicator_y = target
            self.nav_indicator.place_configure(y=target)
            return
        self._indicator_step(target, generation)

    def _indicator_step(self, target, generation):
        if generation != self.nav_animation_generation:
            return
        delta = target - self.nav_indicator_y
        if abs(delta) <= 1:
            self.nav_indicator_y = target
            self.nav_indicator.place_configure(y=target)
            return
        self.nav_indicator_y += delta * 0.28
        self.nav_indicator.place_configure(y=int(self.nav_indicator_y))
        self.after(16, lambda: self._indicator_step(target, generation))

    def _set_progress(self, target, animate=None):
        target = max(0.0, min(1.0, target))
        self.progress_animation_generation += 1
        generation = self.progress_animation_generation
        if animate is None:
            animate = self.animations_enabled
        if not animate:
            self.progress_value = target
            self._render_progress()
            return
        self._progress_step(target, generation)

    def _progress_step(self, target, generation):
        if generation != self.progress_animation_generation:
            return
        delta = target - self.progress_value
        if abs(delta) < 0.006:
            self.progress_value = target
            self._render_progress()
            return
        self.progress_value += delta * 0.14
        self._render_progress()
        self.after(16, lambda: self._progress_step(target, generation))

    def _render_progress(self):
        self.progress.set(self.progress_value)
        self.progress_percent.configure(text=f"{round(self.progress_value * 100)}%")

    def _show_progress(self):
        self.progress_collapse_generation += 1
        self.progress.configure(width=self.PROGRESS_WIDTH, progress_color=self.GREEN)
        self.progress.grid()
        self.progress_percent.grid()

    def _collapse_progress(self):
        self.progress_collapse_generation += 1
        generation = self.progress_collapse_generation
        if not self.animations_enabled:
            self._finish_progress_collapse(generation)
            return

        def step(frame):
            if generation != self.progress_collapse_generation:
                return
            if self.active_operation:
                return
            ratio = min(1.0, frame / 10)
            eased = 1 - (1 - ratio) ** 3
            width = max(1, round(self.PROGRESS_WIDTH * (1 - eased)))
            self.progress.configure(width=width)
            if frame < 10:
                self.after(18, lambda: step(frame + 1))
            else:
                self._finish_progress_collapse(generation)

        step(0)

    def _finish_progress_collapse(self, generation):
        if generation != self.progress_collapse_generation:
            return
        self.progress.grid_remove()
        self.progress_percent.grid_remove()
        self.progress.configure(width=self.PROGRESS_WIDTH)
        self._set_progress(0, animate=False)

    def show_toast(self, text, color=None):
        color = color or self.GREEN
        toast = ctk.CTkFrame(
            self.workspace,
            width=310,
            height=58,
            corner_radius=16,
            fg_color=self.CARD_HOVER,
            border_width=1,
            border_color=color,
        )
        toast.place(relx=1.0, rely=1.0, x=330, y=-86, anchor="se")
        ctk.CTkLabel(
            toast,
            text="●",
            text_color=color,
            font=ctk.CTkFont(size=17),
        ).place(x=16, y=17)
        ctk.CTkLabel(
            toast,
            text=text,
            text_color=self.TEXT,
            font=ctk.CTkFont(self.UI_FONT, 12, "bold"),
        ).place(x=43, y=18)

        def move(x, target, finished):
            if not toast.winfo_exists():
                return
            delta = target - x
            if abs(delta) <= 2:
                toast.place_configure(x=target)
                finished()
                return
            next_x = x + delta * 0.34
            toast.place_configure(x=next_x)
            self.after(16, lambda: move(next_x, target, finished))

        def dismiss():
            if toast.winfo_exists():
                if self.animations_enabled:
                    move(-24, 330, toast.destroy)
                else:
                    toast.destroy()

        def hold():
            self.after(self.notification_duration_ms, dismiss)

        if self.animations_enabled:
            move(330, -24, hold)
        else:
            toast.place_configure(x=-24)
            self.after(self.notification_duration_ms, dismiss)

    # ---------- setup and installation ----------

    def refresh_system_detection(self):
        if not hasattr(self, "spotify_setup_status"):
            return
        self.spotify_setup_status.configure(
            text="◐  Checking Spotify…", text_color=self.ORANGE
        )
        self.spicetify_setup_status.configure(
            text="◐  Checking Spicetify…", text_color=self.ORANGE
        )

        def worker():
            spotify = self._detect_spotify()
            spicetify = {
                "version": self.get_spicetify_version(),
                "path": shutil.which("spicetify.exe"),
            }
            self.ui_queue.put(
                lambda: self._show_system_detection(spotify, spicetify)
            )

        threading.Thread(target=worker, daemon=True).start()

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

    def _show_system_detection(self, spotify, spicetify):
        if spotify["supported"]:
            self.spotify_setup_status.configure(
                text="●  Spotify desktop is ready", text_color=self.GREEN
            )
            self.spotify_setup_detail.configure(
                text=self._short_path(spotify["path"])
            )
            self.download_spotify_button.configure(state="disabled", text="Installed")
        elif spotify["kind"] == "store":
            self.spotify_setup_status.configure(
                text="●  Microsoft Store Spotify found", text_color=self.ORANGE
            )
            self.spotify_setup_detail.configure(
                text="The desktop version is recommended for Spicetify"
            )
            self.download_spotify_button.configure(state="normal", text="Get desktop")
        else:
            self.spotify_setup_status.configure(
                text="●  Spotify was not found", text_color=self.RED
            )
            self.spotify_setup_detail.configure(
                text="Install desktop Spotify, then sign in once"
            )
            self.download_spotify_button.configure(state="normal", text="Download")

        version = spicetify["version"]
        if version:
            self.spicetify_setup_status.configure(
                text=f"●  Spicetify {version} installed", text_color=self.GREEN
            )
            self.spicetify_setup_detail.configure(
                text=self._short_path(spicetify["path"] or "Available on PATH")
            )
            self.install_spicetify_button.configure(state="disabled", text="Installed")
            for button in (
                self.first_setup_button,
                self.remove_modifications_button,
                self.full_uninstall_button,
            ):
                button.configure(state="normal")
        else:
            self.spicetify_setup_status.configure(
                text="●  Spicetify is not installed", text_color=self.RED
            )
            self.spicetify_setup_detail.configure(
                text="Use the official installer below"
            )
            self.install_spicetify_button.configure(state="normal", text="Install")
            for button in (
                self.first_setup_button,
                self.remove_modifications_button,
                self.full_uninstall_button,
            ):
                button.configure(state="disabled")

        if not spotify["supported"]:
            self.first_setup_button.configure(state="disabled")

    @staticmethod
    def _short_path(path, max_length=54):
        path = str(path or "")
        if len(path) <= max_length:
            return path
        return "…" + path[-(max_length - 1) :]

    def install_spicetify(self):
        if self.active_operation:
            self.show_toast("Another operation is already running", self.ORANGE)
            return
        spotify = self._detect_spotify()
        if not spotify["supported"]:
            messagebox.showwarning(
                "Spotify desktop required",
                "Install the desktop version of Spotify and sign in once before "
                "installing Spicetify.",
            )
            return
        if not messagebox.askyesno(
            "Install Spicetify",
            "Download and run the official Spicetify installer from "
            "github.com/spicetify/cli?",
        ):
            return

        self.active_operation = "Preparing Spicetify installer"
        self._cancel_status_reset()
        self._show_progress()
        self.operation_label.configure(
            text="Downloading official installer…", text_color=self.TEXT
        )
        self.top_status.configure(text="  ◐  Preparing install  ", text_color=self.BLUE)
        self.run_button.configure(state="disabled")
        self._set_progress(0, animate=False)
        self._set_progress(0.08)

        def worker():
            installer_path = os.path.join(
                self.data_dir, "spicetify-official-install.ps1"
            )
            try:
                request = urllib.request.Request(
                    self.SPICETIFY_INSTALL_SCRIPT,
                    headers={"User-Agent": f"{self.APP_NAME}/{self.APP_VERSION_FULL}"},
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    installer = response.read()
                if len(installer) < 1000 or b"spicetify" not in installer.lower():
                    raise ValueError("The downloaded installer did not look valid.")
                with open(installer_path, "wb") as installer_file:
                    installer_file.write(installer)
                self.ui_queue.put(
                    lambda: self._launch_spicetify_installer(installer_path)
                )
            except (OSError, ValueError, urllib.error.URLError) as error:
                self.ui_queue.put(lambda problem=error: self._install_download_failed(problem))

        threading.Thread(target=worker, daemon=True).start()

    def _launch_spicetify_installer(self, installer_path):
        self.active_operation = None
        self.run_button.configure(state="normal")
        self.run_operation(
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
            on_success=self.refresh_system_detection,
            on_finish=lambda: self._remove_temporary_file(installer_path),
        )

    def _install_download_failed(self, error):
        self.active_operation = None
        self.run_button.configure(state="normal")
        self._set_progress(0)
        self.operation_label.configure(text="Installer download failed", text_color=self.RED)
        self.top_status.configure(text="  ●  Install failed  ", text_color=self.RED)
        self._schedule_status_reset()
        messagebox.showerror("Install Spicetify", str(error))

    @staticmethod
    def _remove_temporary_file(path):
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass

    def uninstall_spicetify(self):
        if not messagebox.askyesno(
            "Fully uninstall Spicetify",
            "This will restore Spotify and permanently remove Spicetify's program "
            "files, configuration, themes, and extensions for this Windows account.\n\n"
            "Continue?",
        ):
            return
        self.run_operation(
            "Restoring before uninstall",
            ["spicetify", "restore"],
            on_success=self._remove_spicetify_installation,
        )

    def _remove_spicetify_installation(self):
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
        self.show_toast("Spicetify was fully uninstalled")
        self.after(300, self.refresh_system_detection)

    # ---------- application updates ----------

    def check_app_updates(self):
        self.app_update_button.configure(state="disabled", text="Checking…")

        def worker():
            try:
                with open(
                    self.release_config_file, "r", encoding="utf-8"
                ) as config_file:
                    repository = json.load(config_file).get("github_repo", "").strip()
                if not repository:
                    self.ui_queue.put(self._show_unconfigured_update_feed)
                    return
                request = urllib.request.Request(
                    f"https://api.github.com/repos/{repository}/releases/latest",
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": f"{self.APP_NAME}/{self.APP_VERSION_FULL}",
                    },
                )
                with urllib.request.urlopen(request, timeout=12) as response:
                    release = json.load(response)
                self.ui_queue.put(lambda: self._show_app_update_result(release))
            except (OSError, ValueError, urllib.error.URLError) as error:
                self.ui_queue.put(lambda problem=error: self._show_app_update_error(problem))

        threading.Thread(target=worker, daemon=True).start()

    def _show_unconfigured_update_feed(self):
        self.app_update_button.configure(state="normal", text="Check now")
        messagebox.showinfo(
            "Application updates",
            "The update checker is ready, but it needs your future GitHub repository "
            "name in release_config.json before public releases can be checked.",
        )

    def _show_app_update_result(self, release):
        self.app_update_button.configure(state="normal", text="Check now")
        latest_text = str(release.get("tag_name", "")).removeprefix("v")
        try:
            newer = Version(latest_text) > Version(self.APP_VERSION_FULL)
        except InvalidVersion:
            self._show_app_update_error("The release version was not valid.")
            return
        if not newer:
            self.show_toast(f"{self.APP_NAME} is up to date")
            return
        if messagebox.askyesno(
            "Application update available",
            f"{self.APP_NAME} v{latest_text} is available.\n\n"
            "Open the official release page to download it?",
        ):
            webbrowser.open(release.get("html_url", ""))

    def _show_app_update_error(self, error):
        self.app_update_button.configure(state="normal", text="Check now")
        messagebox.showerror("Application updates", f"Could not check for updates:\n{error}")

    # ---------- version status ----------

    def get_spicetify_version(self):
        try:
            result = subprocess.run(
                ["spicetify", "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                startupinfo=self._startup_info(),
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().removeprefix("v")
        except (OSError, subprocess.SubprocessError):
            pass
        return None

    @staticmethod
    def get_latest_release():
        try:
            request = urllib.request.Request(
                "https://api.github.com/repos/spicetify/cli/releases/latest",
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "SauceBoyz-Spicetify-Manager",
                },
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                tag = json.load(response).get("tag_name", "")
                return tag.removeprefix("v") if tag else None
        except (OSError, ValueError, urllib.error.URLError):
            return None

    def check_for_updates(self):
        self.check_button.configure(state="disabled", text="Checking…")
        self._start_spinner()

        def worker():
            current = self.get_spicetify_version()
            latest = self.get_latest_release()
            self.ui_queue.put(lambda: self._show_version_result(current, latest))

        threading.Thread(target=worker, daemon=True).start()

    def _show_version_result(self, current, latest):
        self._stop_spinner()
        self.check_button.configure(state="normal", text="Check again")
        if not current:
            self.hero_title.configure(text="Spicetify was not found")
            self.hero_detail.configure(
                text="Install Spicetify or add its executable to PATH."
            )
            self.top_status.configure(text="  ●  Needs attention  ", text_color=self.RED)
        elif latest and current != latest:
            self.hero_title.configure(text=f"Version {latest} is available")
            self.hero_detail.configure(text=f"You currently have Spicetify {current}.")
            self.top_status.configure(text="  ●  Update available  ", text_color=self.ORANGE)
        else:
            self.hero_title.configure(text="Spicetify is up to date")
            detail = f"Spicetify {current} is ready to use."
            if not latest:
                detail += " The online release check is unavailable."
            self.hero_detail.configure(text=detail)
            self.top_status.configure(text="  ●  Ready  ", text_color=self.GREEN)

    def _start_spinner(self):
        self._stop_spinner()
        frames = ("◐", "◓", "◑", "◒")

        def tick():
            self.top_status.configure(
                text=f"  {frames[self.spinner_frame % len(frames)]}  Checking  ",
                text_color=self.ORANGE,
            )
            self.spinner_frame += 1
            self.spinner_job = self.after(110, tick)

        tick()

    def _stop_spinner(self):
        if self.spinner_job:
            self.after_cancel(self.spinner_job)
            self.spinner_job = None

    # ---------- command execution ----------

    def run_update(self):
        self.run_operation("Updating theme", ["spicetify", "update"])

    def run_upgrade(self):
        self.run_operation("Upgrading Spicetify", ["spicetify", "upgrade"])

    def run_backup_apply(self):
        self.run_operation(
            "Backing up and applying",
            ["spicetify", "backup", "apply"],
        )

    def run_restore(self):
        if messagebox.askyesno(
            "Restore Spotify",
            "Remove Spicetify modifications and restore Spotify to its original state?",
        ):
            self.run_operation("Restoring Spotify", ["spicetify", "restore"])

    def run_custom_command(self):
        command = self.command_entry.get().strip()
        if not command:
            self.show_toast("Enter a command first", self.ORANGE)
            return
        self.run_operation(
            "Running custom command",
            ["cmd.exe", "/d", "/s", "/c", command],
            display_command=command,
        )

    def run_operation(
        self,
        label,
        command,
        display_command=None,
        on_success=None,
        on_finish=None,
    ):
        if self.active_operation:
            self.show_toast("Another operation is already running", self.ORANGE)
            return
        self.active_operation = label
        self._cancel_status_reset()
        self._show_progress()
        self.operation_label.configure(text=label, text_color=self.TEXT)
        self.top_status.configure(text=f"  ◐  {label}  ", text_color=self.BLUE)
        self.run_button.configure(state="disabled")
        self.cancel_button.configure(
            state="normal", text_color=self.TEXT, border_color=self.RED
        )
        self._set_progress(0, animate=False)
        self._set_progress(0.08)
        shown = display_command or subprocess.list2cmdline(command)
        self._write_output(f"\n> {shown}\n")

        def worker():
            return_code = 1
            lines_seen = 0
            try:
                self.active_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=os.path.expanduser("~"),
                    startupinfo=self._startup_info(),
                )
                while True:
                    line = self.active_process.stdout.readline()
                    if line == "" and self.active_process.poll() is not None:
                        break
                    if line:
                        self._write_output(strip_ansi(line))
                        lines_seen += 1
                        staged_progress = min(0.88, 0.18 + lines_seen * 0.05)
                        self.ui_queue.put(
                            lambda value=staged_progress: self._set_progress(value)
                        )
                return_code = self.active_process.wait()
            except OSError as error:
                self._write_output(f"Error: {error}\n")
            finally:
                self.active_process = None
                self.ui_queue.put(
                    lambda code=return_code, name=label: self._operation_finished(
                        name, code, on_success, on_finish
                    )
                )

        threading.Thread(target=worker, daemon=True).start()

    def cancel_operation(self):
        process = self.active_process
        if process and process.poll() is None:
            process.terminate()
            self._write_output("\nOperation cancelled by user.\n")
            self.operation_label.configure(text="Cancelling…", text_color=self.ORANGE)

    def _operation_finished(
        self, label, return_code, on_success=None, on_finish=None
    ):
        self.active_operation = None
        self.run_button.configure(state="normal")
        self.cancel_button.configure(
            state="disabled", text_color=self.MUTED, border_color=self.BORDER
        )
        if return_code == 0:
            self._set_progress(1.0, animate=False)
            self.operation_label.configure(text="Completed", text_color=self.GREEN)
            self.top_status.configure(text="  ●  Completed  ", text_color=self.GREEN)
            self._schedule_status_reset()
            self._write_output(f"{label} completed successfully.\n")
            self.show_toast(f"{label} completed")
            if on_success:
                try:
                    on_success()
                except Exception as error:
                    self._write_output(f"Post-operation step failed: {error}\n")
                    messagebox.showerror(
                        "Operation incomplete",
                        f"The command completed, but cleanup failed:\n{error}",
                    )
            if "Upgrading" in label:
                self.check_for_updates()
        else:
            self._set_progress(0)
            self.operation_label.configure(
                text=f"Failed · exit code {return_code}", text_color=self.RED
            )
            self.top_status.configure(text="  ●  Action failed  ", text_color=self.RED)
            self._schedule_status_reset()
            self._write_output(f"{label} failed with exit code {return_code}.\n")
            self.show_toast(f"{label} failed", self.RED)
        if on_finish:
            try:
                on_finish()
            except Exception as error:
                self._write_output(f"Cleanup step failed: {error}\n")

    def _write_output(self, text):
        logfile = self._ensure_current_logfile()
        with self.log_lock:
            try:
                with open(logfile, "a", encoding="utf-8") as log:
                    log.write(text)
            except OSError:
                pass
        self.ui_queue.put(lambda value=text: self._append_console(value))

    def _ensure_current_logfile(self):
        if self.current_logfile:
            return self.current_logfile
        os.makedirs(self.log_dir, exist_ok=True)
        self.current_logfile = os.path.join(
            self.log_dir, f"session_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        return self.current_logfile

    def _append_console(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")

    # ---------- logs and settings ----------

    def refresh_logs(self):
        files = []
        for path in glob.glob(os.path.join(self.log_dir, "*.log")):
            try:
                if os.path.getsize(path) > 0:
                    files.append(path)
            except OSError:
                pass
        files.sort(reverse=True)
        names = [os.path.basename(path) for path in files] or ["No logs"]
        self.log_session.configure(values=names)
        selection = self.log_session.get()
        if selection not in names:
            selection = names[0]
            self.log_session.set(selection)
        self.load_log_session(selection)

    def load_log_session(self, selection):
        if not selection or selection == "No logs":
            self.full_log_content = ""
        else:
            try:
                with open(
                    os.path.join(self.log_dir, selection), "r", encoding="utf-8"
                ) as log:
                    self.full_log_content = log.read()
            except OSError as error:
                self.full_log_content = f"Could not load log: {error}"
        self.filter_log()

    def filter_log(self):
        term = self.log_search.get().strip().lower()
        content = self.full_log_content
        if term:
            content = "\n".join(
                line for line in content.splitlines() if term in line.lower()
            )
        self.logs_text.configure(state="normal")
        self.logs_text.delete("1.0", "end")
        self.logs_text.insert("1.0", content or "This session has no activity yet.")
        self.logs_text.configure(state="disabled")

    def save_log_copy(self):
        content = self.full_log_content.strip()
        if not content:
            self.show_toast("There is no log content to save", self.ORANGE)
            return
        destination = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")],
        )
        if destination:
            try:
                with open(destination, "w", encoding="utf-8") as output:
                    output.write(content + "\n")
                self.show_toast("Log copy saved")
            except OSError as error:
                messagebox.showerror("Save log", str(error))

    def _selected_log_path(self):
        selection = os.path.basename(self.log_session.get().strip())
        if not selection or selection == "No logs":
            return None
        path = os.path.abspath(os.path.join(self.log_dir, selection))
        if os.path.commonpath((path, os.path.abspath(self.log_dir))) != os.path.abspath(
            self.log_dir
        ):
            return None
        return path

    def clear_selected_log(self):
        path = self._selected_log_path()
        if not path or not os.path.exists(path):
            self.show_toast("Select a log session first", self.ORANGE)
            return
        if not messagebox.askyesno(
            "Clear selected log",
            f"Remove all entries from {os.path.basename(path)}?",
        ):
            return
        try:
            open(path, "w", encoding="utf-8").close()
        except OSError as error:
            messagebox.showerror("Clear log", str(error))
            return
        self.load_log_session(os.path.basename(path))
        self.show_toast("Selected log cleared")

    def delete_selected_log(self):
        path = self._selected_log_path()
        if not path or not os.path.exists(path):
            self.show_toast("Select a log session first", self.ORANGE)
            return
        if self.current_logfile and os.path.abspath(path) == os.path.abspath(
            self.current_logfile
        ):
            messagebox.showinfo(
                "Active session log",
                "The active session log cannot be deleted while the manager is running. "
                "You can clear it now or delete it after restarting the app.",
            )
            return
        if not messagebox.askyesno(
            "Delete selected log",
            f"Permanently delete {os.path.basename(path)}?",
        ):
            return
        try:
            os.remove(path)
        except OSError as error:
            messagebox.showerror("Delete log", str(error))
            return
        self.refresh_logs()
        self.show_toast("Selected log deleted")

    def open_logs_folder(self):
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            os.startfile(self.log_dir)
        except OSError as error:
            messagebox.showerror("Open logs folder", str(error))

    def change_scale(self, scale):
        ctk.set_widget_scaling(int(scale.rstrip("%")) / 100)
        self.settings["interface_scale"] = scale
        self._save_settings()
        self.show_toast(f"Interface scale set to {scale}")

    def toggle_animations(self):
        self.animations_enabled = bool(self.motion_switch.get())
        self.settings["animations_enabled"] = self.animations_enabled
        self._save_settings()
        self.show_toast(
            "Interface motion enabled"
            if self.animations_enabled
            else "Interface motion reduced"
        )

    def change_notification_duration(self, duration):
        self.notification_duration_ms = self.NOTIFICATION_DURATIONS[duration]
        self.settings["notification_duration"] = duration
        self._save_settings()
        self.show_toast(f"Notifications will stay for {duration}")

    def toggle_always_on_top(self):
        enabled = bool(self.always_on_top_switch.get())
        self.attributes("-topmost", enabled)
        self.settings["always_on_top"] = enabled
        self._save_settings()
        self.show_toast("Always on top enabled" if enabled else "Always on top disabled")

    def _cancel_status_reset(self):
        if self.status_reset_job:
            self.after_cancel(self.status_reset_job)
            self.status_reset_job = None

    def _schedule_status_reset(self):
        self._cancel_status_reset()

        def reset():
            self.status_reset_job = None
            if not self.active_operation:
                self.top_status.configure(text="  ●  Ready  ", text_color=self.GREEN)
                self.operation_label.configure(text="Idle", text_color=self.MUTED)
                self._collapse_progress()

        self.status_reset_job = self.after(self.notification_duration_ms, reset)

    # ---------- infrastructure ----------

    def _migrate_legacy_settings(self):
        if os.path.exists(self.settings_file):
            return
        legacy_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "settings.json"
        )
        if os.path.abspath(legacy_file) == os.path.abspath(self.settings_file):
            return
        try:
            if os.path.isfile(legacy_file):
                shutil.copy2(legacy_file, self.settings_file)
        except OSError:
            pass

    def _load_settings(self):
        settings = dict(self.DEFAULT_SETTINGS)
        try:
            with open(self.settings_file, "r", encoding="utf-8") as settings_file:
                saved = json.load(settings_file)
            if isinstance(saved, dict):
                settings.update(
                    {
                        key: saved[key]
                        for key in self.DEFAULT_SETTINGS
                        if key in saved
                    }
                )
        except (OSError, ValueError):
            pass
        if settings["interface_scale"] not in {"90%", "100%", "110%"}:
            settings["interface_scale"] = "100%"
        if settings["notification_duration"] not in self.NOTIFICATION_DURATIONS:
            settings["notification_duration"] = "3 seconds"
        settings["animations_enabled"] = bool(settings["animations_enabled"])
        settings["always_on_top"] = bool(settings["always_on_top"])
        return settings

    def _save_settings(self):
        temporary_file = self.settings_file + ".tmp"
        try:
            with open(temporary_file, "w", encoding="utf-8") as settings_file:
                json.dump(self.settings, settings_file, indent=2)
            os.replace(temporary_file, self.settings_file)
        except OSError:
            try:
                if os.path.exists(temporary_file):
                    os.remove(temporary_file)
            except OSError:
                pass

    @staticmethod
    def _startup_info():
        if platform.system() == "Windows":
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return info
        return None

    def _drain_ui_queue(self):
        try:
            while True:
                callback = self.ui_queue.get_nowait()
                callback()
        except queue.Empty:
            pass
        if self.winfo_exists():
            self.after(40, self._drain_ui_queue)

    def _on_close(self):
        process = self.active_process
        if process and process.poll() is None:
            process.terminate()
        self.destroy()


def strip_ansi(text):
    return re.sub(r"\x1B[@-_][0-?]*[ -/]*[@-~]", "", text)


if __name__ == "__main__":
    app = SpicetifyManager(preview_update="--preview-update" in sys.argv)
    app.mainloop()
