import sys
import os
import json
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLineEdit, QTabWidget, QDialog,
    QCheckBox, QListWidget, QListWidgetItem, QLabel, QInputDialog,
    QMessageBox, QMenu, QComboBox, QFormLayout
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence
from urllib.parse import quote_plus

from config_loader import build_stylesheet, load_config

ONBOARDING_TEST_MODE = False
SEARCH_PROVIDERS = {
    "Google": "https://www.google.com/search?q=${query}",
    "DuckDuckGo": "https://duckduckgo.com/?q=${query}",
    "Bing": "https://www.bing.com/search?q=${query}",
    "Brave": "https://search.brave.com/search?q=${query}",
}

APP_STYLESHEET = """
    QMainWindow { background-color: #2E2E2E; }
    QDialog { background-color: #2E2E2E; }
    QLabel {
        color: white;
        font-size: 14px;
    }
    QLineEdit {
        border-radius: 5px;
        padding: 5px;
        background-color: #444;
        color: white;
        font-size: 14px;
    }
    QPushButton {
        background-color: #444;
        color: white;
        border: 2px solid #555;
        border-radius: 5px;
        padding: 5px 10px;
    }
    QPushButton:hover { background-color: #555; }
    QPushButton:pressed { background-color: #666; }
    QListWidget {
        background-color: #3A3A3A;
        color: white;
        border-radius: 5px;
    }
    QTabBar::tab {
        background-color: #444;
        color: white;
        padding: 10px 10px;
        font-size: 14px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }
    QTabBar::tab:selected {
        background-color: #555;
    }
    QTabBar::tab:hover {
        background-color: #555;
    }
"""

class ProfileManager(QDialog):
    def __init__(self, stylesheet: str | None = None):
        super().__init__()
        self.setWindowTitle("Profile Manager")
        # if logo exists, set it on the dialog as well
        logo_path = os.path.join("icons", "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
        self.setGeometry(400, 200, 400, 300)
        self.setStyleSheet(stylesheet or APP_STYLESHEET)

        self.profiles_folder = "profiles"
        os.makedirs(self.profiles_folder, exist_ok=True)

        layout = QVBoxLayout()

        self.list_widget = QListWidget()
        self.load_profiles()
        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()

        select_button = QPushButton("Select")
        select_button.clicked.connect(self.select_profile)
        button_layout.addWidget(select_button)

        new_button = QPushButton("Create New")
        new_button.clicked.connect(self.create_profile)
        button_layout.addWidget(new_button)

        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_profile)
        button_layout.addWidget(delete_button)

        exit_button = QPushButton("Exit")
        exit_button.clicked.connect(self.reject)
        button_layout.addWidget(exit_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.selected_profile = None

    def load_profiles(self):
        self.list_widget.clear()
        profiles = [d for d in os.listdir(self.profiles_folder) if os.path.isdir(os.path.join(self.profiles_folder, d))]
        for profile in profiles:
            self.list_widget.addItem(profile)

    def select_profile(self):
        selected = self.list_widget.currentItem()
        if selected:
            self.selected_profile = selected.text()
            self.accept()

    def create_profile(self):
        name, ok = QInputDialog.getText(self, "Create Profile", "Enter profile name:")
        if ok and name:
            path = os.path.join(self.profiles_folder, name)
            if not os.path.exists(path):
                os.makedirs(path)
                os.makedirs(os.path.join(path, "browser_data"))
                self.load_profiles()
            else:
                QMessageBox.warning(self, "Error", "Profile already exists.")

    def delete_profile(self):
        selected = self.list_widget.currentItem()
        if selected:
            reply = QMessageBox.question(self, "Delete Profile", f"Are you sure you want to delete '{selected.text()}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                shutil.rmtree(os.path.join(self.profiles_folder, selected.text()))
                self.load_profiles()

class BrowserTab(QWidget):
    def __init__(self, profile, home_url, plugins, browser_ref):
        super().__init__()
        self.browser_ref = browser_ref
        self.browser = QWebEngineView()
        self.page = QWebEnginePage(profile, self)
        self.browser.setPage(self.page)
        self.browser.setUrl(QUrl(home_url))

        self.plugins = plugins
        self.browser.loadFinished.connect(self.inject_plugins)
        self.browser.urlChanged.connect(self.url_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self.browser)
        self.setLayout(layout)

    def inject_plugins(self):
        for name, js in self.plugins.items():
            self.browser.page().runJavaScript(js)

    def url_changed(self, url):
        # Notify the main window so it can update history and URL bar
        self.browser_ref.on_tab_url_changed(url, self)


class FirstRunOnboardingDialog(QDialog):
    """Collect first-run settings and optionally generate Lua config files."""

    def __init__(self, current_config: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("First-Run Setup")
        self.resize(520, 420)
        self._result = None
        self.current_config = current_config or {}

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Configure startup defaults for Tarium.\n"
            "These options generate global Lua config files."
        )
        layout.addWidget(intro)

        form = QFormLayout()

        self.home_input = QLineEdit(self.current_config.get("home_url", "https://example.com"))
        form.addRow("Home / Start page:", self.home_input)

        self.search_combo = QComboBox()
        self.search_combo.addItems(list(SEARCH_PROVIDERS.keys()))
        current_search = (self.current_config.get("search") or {}).get("template", "")
        if current_search:
            for name, template in SEARCH_PROVIDERS.items():
                if template == current_search:
                    self.search_combo.setCurrentText(name)
                    break
        form.addRow("Search provider:", self.search_combo)

        self.enable_keybinds = QCheckBox("Enable keyboard shortcuts")
        self.enable_keybinds.setChecked(True)
        form.addRow("", self.enable_keybinds)

        self.new_tab_key = QComboBox()
        self.new_tab_key.addItems(["T", "N", "K"])
        self.new_tab_key.setCurrentText("T")
        form.addRow("New tab key (Ctrl+):", self.new_tab_key)

        self.close_tab_key = QComboBox()
        self.close_tab_key.addItems(["W", "Q", "X"])
        self.close_tab_key.setCurrentText("W")
        form.addRow("Close tab key (Ctrl+):", self.close_tab_key)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (default)", "Light"])
        form.addRow("Theme preset:", self.theme_combo)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._on_apply)
        buttons.addWidget(apply_btn)
        layout.addLayout(buttons)

    def _theme_preset(self) -> dict:
        if self.theme_combo.currentText().startswith("Light"):
            return {
                "background": "#F2F2F2",
                "surface": "#FFFFFF",
                "surface_hover": "#E5E5E5",
                "surface_pressed": "#D6D6D6",
                "text": "#111111",
                "list_bg": "#FFFFFF",
                "tab_bg": "#ECECEC",
                "tab_selected": "#DDDDDD",
                "tab_hover": "#E2E2E2",
            }
        return {
            "background": "#2E2E2E",
            "surface": "#444444",
            "surface_hover": "#555555",
            "surface_pressed": "#666666",
            "text": "#FFFFFF",
            "list_bg": "#3A3A3A",
            "tab_bg": "#444444",
            "tab_selected": "#555555",
            "tab_hover": "#555555",
        }

    def _build_keybinds(self) -> dict:
        if not self.enable_keybinds.isChecked():
            return {}
        new_tab_seq = f"Ctrl+{self.new_tab_key.currentText()}"
        close_tab_seq = f"Ctrl+{self.close_tab_key.currentText()}"
        if new_tab_seq == close_tab_seq:
            raise ValueError("New tab and close tab shortcuts must be different.")
        return {
            new_tab_seq: "new_tab",
            close_tab_seq: "close_tab",
            "Ctrl+1": "switch_tab_1",
            "Ctrl+2": "switch_tab_2",
            "Ctrl+3": "switch_tab_3",
            "Ctrl+4": "switch_tab_4",
            "Ctrl+5": "switch_tab_5",
            "Ctrl+6": "switch_tab_6",
            "Ctrl+7": "switch_tab_7",
            "Ctrl+8": "switch_tab_8",
            "Ctrl+9": "switch_tab_9",
        }

    def _on_apply(self):
        home_url = self.home_input.text().strip()
        if not (home_url.startswith("http://") or home_url.startswith("https://")):
            QMessageBox.warning(self, "Invalid URL", "Home URL must start with http:// or https://.")
            return
        try:
            keybinds = self._build_keybinds()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid keybinds", str(exc))
            return

        search_template = SEARCH_PROVIDERS[self.search_combo.currentText()]
        self._result = {
            "theme": self._theme_preset(),
            "home_url": home_url,
            "search": {"template": search_template},
            "keybinds": keybinds,
        }
        self.accept()

    def get_config(self) -> dict | None:
        return self._result


def _dict_to_lua_table(data: dict, indent: int = 0) -> str:
    pad = " " * indent
    lines = ["{"]
    for key, value in data.items():
        lua_key = f"[\"{key}\"]"
        if isinstance(value, dict):
            lines.append(f"{pad}  {lua_key} = {_dict_to_lua_table(value, indent + 2)},")
        elif isinstance(value, str):
            safe = value.replace("\\", "\\\\").replace("\"", "\\\"")
            lines.append(f'{pad}  {lua_key} = "{safe}",')
        else:
            lines.append(f"{pad}  {lua_key} = {value},")
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def write_lua_config_files(config: dict):
    os.makedirs("config", exist_ok=True)
    theme_content = "return {\n  theme = " + _dict_to_lua_table(config["theme"], 2) + ",\n}\n"
    web_content = (
        "return {\n"
        f"  home_url = \"{config['home_url']}\",\n"
        "  search = {\n"
        f"    template = \"{config['search']['template']}\",\n"
        "  },\n"
        "}\n"
    )
    keybinds_content = "return {\n  keybinds = " + _dict_to_lua_table(config.get("keybinds", {}), 2) + ",\n}\n"

    with open(os.path.join("config", "theme.lua"), "w", encoding="utf-8") as f:
        f.write(theme_content)
    with open(os.path.join("config", "web.lua"), "w", encoding="utf-8") as f:
        f.write(web_content)
    with open(os.path.join("config", "keybinds.lua"), "w", encoding="utf-8") as f:
        f.write(keybinds_content)


def should_open_onboarding(config_errors: list[str]) -> tuple[bool, bool]:
    """Return (open_onboarding, auto_open)."""
    if not config_errors:
        return False, False
    missing_files = any("No .lua files found" in err for err in config_errors)
    if missing_files:
        return True, True
    return True, False

class WebBrowser(QMainWindow):
    def __init__(self, profile_name, config: dict):
        super().__init__()
        self.profile_name = profile_name
        self.profile_path = os.path.join("profiles", self.profile_name)

        self.setWindowTitle(f"Tarium Browser - {self.profile_name}")
        # Use the supplied logo as the window icon if available
        logo_path = os.path.join("icons", "logo.png")
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
        self.setGeometry(200, 200, 1024, 768)
        self.home_url = config["home_url"]
        self.search_template = config["search"]["template"]

        self.data_folder = self.profile_path
        os.makedirs(self.data_folder, exist_ok=True)
        self.plugins_folder = "./plugins"
        os.makedirs(self.plugins_folder, exist_ok=True)

        profile_storage_path = os.path.abspath(os.path.join(self.data_folder, "browser_data"))
        os.makedirs(profile_storage_path, exist_ok=True)
        self.profile = QWebEngineProfile(self.profile_name, self)
        self.profile.setPersistentStoragePath(profile_storage_path)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

        self.enabled_plugins = self.load_enabled_plugins()
        self.available_plugins = self.load_plugins()

        self.bookmarks = self.load_json("bookmarks.json")
        self.history = self.load_json("history.json")

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_current_tab_changed)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Enter URL...")
        self.url_bar.returnPressed.connect(self.load_url)

        def create_icon_button(icon_path, callback):
            button = QPushButton()
            button.setIcon(QIcon(icon_path))
            button.setFixedSize(40, 40)
            button.clicked.connect(callback)
            return button

        back_button = create_icon_button("icons/back.png", self.go_back)
        forward_button = create_icon_button("icons/forward.png", self.go_forward)
        refresh_button = create_icon_button("icons/refresh.png", self.refresh_page)
        home_button = create_icon_button("icons/home.png", self.go_home)
        go_button = create_icon_button("icons/go.png", self.load_url)
        new_tab_button = create_icon_button("icons/new_tab.png", self.add_new_tab)
        bookmarks_button = create_icon_button("icons/bookmark.png", self.show_bookmarks)
        history_button = create_icon_button("icons/history.png", self.show_history)
        plugins_button = create_icon_button("icons/plugin.png", self.show_plugins_menu)

        # Hamburger menu for About and metadata
        menu_button = QPushButton()
        menu_button.setIcon(QIcon("icons/hambuger_dropdown.png"))
        menu_button.setFixedSize(40, 40)
        menu_button.clicked.connect(self.show_hamburger_menu)

        toolbar_layout = QHBoxLayout()
        for btn in [
            back_button,
            forward_button,
            self.url_bar,
            go_button,
            refresh_button,
            home_button,
            new_tab_button,
            bookmarks_button,
            history_button,
            plugins_button,
            menu_button,
        ]:
            toolbar_layout.addWidget(btn)
        toolbar_layout.setSpacing(10)

        main_layout = QVBoxLayout()
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.tabs)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.setStyleSheet(build_stylesheet(config["theme"]))

        self.add_new_tab()

        self._register_keybinds(config.get("keybinds") or {})

    def _register_keybinds(self, keybinds: dict):
        """Register keyboard shortcuts from config. Keys are key sequences (e.g. 'Ctrl+T')."""
        for seq_str, action in keybinds.items():
            seq_str = str(seq_str).strip()
            if not seq_str:
                continue
            try:
                qseq = QKeySequence(seq_str)
                if qseq.isEmpty():
                    continue
            except Exception:
                continue
            if isinstance(action, str):
                if action == "new_tab":
                    QShortcut(qseq, self, activated=self.add_new_tab)
                elif action == "close_tab":
                    QShortcut(qseq, self, activated=self.close_current_tab)
                elif action in {f"switch_tab_{i}" for i in range(1, 10)}:
                    idx = int(action.split("_")[-1]) - 1
                    QShortcut(qseq, self, activated=lambda i=idx: self.activate_tab(i))
            elif isinstance(action, dict):
                act = action.get("action")
                url = action.get("url")
                if act == "new_tab_url" and url and str(url).strip().startswith("http"):
                    u = str(url).strip()
                    QShortcut(qseq, self, activated=lambda uu=u: self.open_url_in_new_tab(uu))
                elif act == "replace_tab_url" and url and str(url).strip().startswith("http"):
                    u = str(url).strip()
                    QShortcut(qseq, self, activated=lambda uu=u: self.replace_current_tab_url(uu))

    def open_url_in_new_tab(self, url: str):
        """Open a URL in a new tab and switch to it."""
        self.add_new_tab()
        browser = self.current_browser()
        if browser:
            browser.setUrl(QUrl(url))

    def replace_current_tab_url(self, url: str):
        """Navigate the current tab to the given URL."""
        browser = self.current_browser()
        if browser:
            browser.setUrl(QUrl(url))

    def load_json(self, filename):
        path = os.path.join(self.data_folder, filename)
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return []

    def save_json(self, filename, data):
        path = os.path.join(self.data_folder, filename)
        with open(path, "w") as f:
            json.dump(data, f)

    def current_browser(self):
        current_tab = self.tabs.currentWidget()
        return current_tab.browser if current_tab else None

    def add_new_tab(self):
        self.available_plugins = self.load_plugins()
        new_tab = BrowserTab(self.profile, self.home_url, self.available_plugins, self)
        index = self.tabs.addTab(new_tab, "New Tab")
        self.tabs.setCurrentIndex(index)
        self._bind_tab_signals(new_tab)

    def _bind_tab_signals(self, tab: BrowserTab):
        """Ensure tab title and icon always match the correct tab, even when reordered."""

        def handle_title_changed(title, t=tab):
            idx = self.tabs.indexOf(t)
            if idx != -1:
                self.tabs.setTabText(idx, title or "New Tab")

        def handle_icon_changed(icon, t=tab):
            idx = self.tabs.indexOf(t)
            if idx != -1:
                self.tabs.setTabIcon(idx, icon)

        tab.browser.titleChanged.connect(handle_title_changed)
        tab.browser.iconChanged.connect(handle_icon_changed)

    def close_current_tab(self):
        index = self.tabs.currentIndex()
        if index >= 0:
            self.close_tab(index)

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget:
            widget.browser.page().deleteLater()
            widget.browser.deleteLater()
            widget.deleteLater()
        self.tabs.removeTab(index)
        if self.tabs.count() == 0:
            self.close()

    def load_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return

        # If it looks like a URL (has a dot or scheme), treat it as a URL.
        if "://" in text or "." in text:
            url_str = text
            if not url_str.startswith("http://") and not url_str.startswith("https://"):
                url_str = "http://" + url_str
            qurl = QUrl(url_str)
        else:
            # Treat as a search query; use template from config (e.g. ${query})
            query = quote_plus(text)
            url_str = self.search_template.replace("${query}", query)
            qurl = QUrl(url_str)

        browser = self.current_browser()
        if browser:
            browser.setUrl(qurl)

    def go_home(self):
        browser = self.current_browser()
        if browser:
            browser.setUrl(QUrl(self.home_url))

    def refresh_page(self):
        browser = self.current_browser()
        if browser:
            browser.reload()

    def go_back(self):
        browser = self.current_browser()
        if browser:
            browser.back()

    def go_forward(self):
        browser = self.current_browser()
        if browser:
            browser.forward()

    def show_plugins_menu(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Manage Plugins")
        dlg.resize(400, 300)
        layout = QVBoxLayout()

        for plugin_name in self.load_all_plugin_names():
            cb = QCheckBox(plugin_name)
            cb.setChecked(plugin_name in self.enabled_plugins)
            cb.toggled.connect(lambda checked, name=plugin_name: self.toggle_plugin(name, checked))
            layout.addWidget(cb)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        layout.addLayout(buttons_layout)

        dlg.setLayout(layout)
        dlg.setStyleSheet(self.styleSheet())
        dlg.exec()

    def load_all_plugin_names(self):
        return [f[:-3] for f in os.listdir(self.plugins_folder) if f.endswith(".js")]

    def load_enabled_plugins(self):
        path = os.path.join(self.data_folder, "enabled.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return set(json.load(f))
        return set()

    def save_enabled_plugins(self):
        path = os.path.join(self.data_folder, "enabled.json")
        with open(path, "w") as f:
            json.dump(list(self.enabled_plugins), f)

    def toggle_plugin(self, name, enabled):
        if enabled:
            self.enabled_plugins.add(name)
        else:
            self.enabled_plugins.discard(name)
        self.save_enabled_plugins()

    def load_plugins(self):
        plugins = {}
        for filename in os.listdir(self.plugins_folder):
            if filename.endswith(".js"):
                name = filename[:-3]
                if name in self.enabled_plugins:
                    with open(os.path.join(self.plugins_folder, filename), "r", encoding="utf-8") as f:
                        plugins[name] = f.read()
        return plugins

    def save_history(self, url):
        self.history.append(url)
        self.save_json("history.json", self.history)

    def activate_tab(self, index: int):
        """Switch to tab at the given index, if it exists."""
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def on_tab_url_changed(self, url, tab):
        """Update history and URL bar when a tab's URL changes."""
        url_str = url.toString()
        self.save_history(url_str)

        # Only update the URL bar if this is the active tab
        if self.tabs.currentWidget() is tab:
            if url_str == self.home_url:
                # On home page, keep the bar empty with its placeholder
                self.url_bar.clear()
            else:
                self.url_bar.setText(url_str)

    def on_current_tab_changed(self, index: int):
        """Keep URL bar in sync when the active tab changes."""
        tab = self.tabs.widget(index)
        if tab is None:
            self.url_bar.clear()
            return
        url_str = tab.browser.url().toString()
        if not url_str or url_str == self.home_url:
            self.url_bar.clear()
        else:
            self.url_bar.setText(url_str)

    def show_bookmarks(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Bookmarks")
        dlg.resize(500, 400)
        layout = QVBoxLayout()
        list_widget = QListWidget()

        for bm in self.bookmarks:
            item = QListWidgetItem(bm)
            list_widget.addItem(item)

        def remove_selected_bookmark():
            selected = list_widget.currentItem()
            if selected:
                self.bookmarks.remove(selected.text())
                self.save_json("bookmarks.json", self.bookmarks)
                list_widget.takeItem(list_widget.row(selected))

        list_widget.itemDoubleClicked.connect(lambda item: self.load_bookmark(item.text()))
        layout.addWidget(list_widget)

        add_current = QPushButton("Add Current Page")
        add_current.clicked.connect(lambda: self.add_current_bookmark(list_widget))
        layout.addWidget(add_current)

        remove_current = QPushButton("Remove Selected Bookmark")
        remove_current.clicked.connect(remove_selected_bookmark)
        layout.addWidget(remove_current)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        layout.addLayout(buttons_layout)

        dlg.setLayout(layout)
        dlg.setStyleSheet(self.styleSheet())
        dlg.exec()

    def load_bookmark(self, url):
        browser = self.current_browser()
        if browser:
            browser.setUrl(QUrl(url))

    def add_current_bookmark(self, list_widget=None):
        browser = self.current_browser()
        if browser:
            url = browser.url().toString()
            if url not in self.bookmarks:
                self.bookmarks.append(url)
                self.save_json("bookmarks.json", self.bookmarks)
                if list_widget is not None:
                    list_widget.addItem(QListWidgetItem(url))

    def show_history(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("History")
        dlg.resize(500, 400)
        layout = QVBoxLayout()
        list_widget = QListWidget()

        for url in reversed(self.history[-200:]):
            item = QListWidgetItem(url)
            list_widget.addItem(item)

        list_widget.itemDoubleClicked.connect(lambda item: self.load_bookmark(item.text()))
        layout.addWidget(list_widget)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(close_btn)
        layout.addLayout(buttons_layout)

        dlg.setLayout(layout)
        dlg.setStyleSheet(self.styleSheet())
        dlg.exec()

    def show_about(self):
        # Currently unused, but kept for potential future expansion.
        # Shown via the hamburger menu as inline text instead of a dialog.
        pass

    def show_hamburger_menu(self):
        """Show a small dropdown menu with About information."""
        menu = QMenu(self)

        title_action = menu.addAction("Tarium Browser")
        title_action.setEnabled(False)

        version_action = menu.addAction("Version 1.0.0")
        version_action.setEnabled(False)

        desc_action = menu.addAction("Minimal Qt WebEngine browser")
        desc_action.setEnabled(False)

        menu.addSeparator()
        copyright_action = menu.addAction("\u00a9 2026 Tarium")
        copyright_action.setEnabled(False)

        # Position the menu just under the hamburger button
        sender = self.sender()
        if isinstance(sender, QPushButton):
            menu.exec(sender.mapToGlobal(sender.rect().bottomLeft()))
        else:
            menu.exec(self.mapToGlobal(self.rect().center()))

if __name__ == "__main__":
    app = QApplication(sys.argv)

    config, config_errors = load_config()
    if ONBOARDING_TEST_MODE:
        onboarding = FirstRunOnboardingDialog(current_config=config)
        if onboarding.exec() == QDialog.DialogCode.Accepted and onboarding.get_config():
            config = onboarding.get_config()
        elif config is None:
            QMessageBox.critical(
                None,
                "Config Error",
                "Onboarding test mode did not produce a valid config. The browser will exit.",
            )
            sys.exit(1)
    elif config_errors or config is None:
        open_onboarding, auto_open = should_open_onboarding(config_errors or ["No config returned."])
        accepted = False
        if open_onboarding:
            if auto_open:
                accepted = True
            else:
                reply = QMessageBox.question(
                    None,
                    "Config Error",
                    "Invalid config detected.\n\n"
                    + "\n".join(config_errors or ["No config returned."])
                    + "\n\nOpen onboarding to generate config files?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                accepted = reply == QMessageBox.StandardButton.Yes
        if accepted:
            onboarding = FirstRunOnboardingDialog(current_config=config)
            if onboarding.exec() == QDialog.DialogCode.Accepted and onboarding.get_config():
                write_lua_config_files(onboarding.get_config())
                config, config_errors = load_config()

        if config_errors or config is None:
            QMessageBox.critical(
                None,
                "Config Error",
                "Invalid or missing config. The browser will exit.\n\n"
                + "\n".join(config_errors or ["No config returned."]),
            )
            sys.exit(1)

    stylesheet = build_stylesheet(config["theme"])

    manager = ProfileManager(stylesheet=stylesheet)
    if manager.exec() == QDialog.DialogCode.Accepted:
        window = WebBrowser(manager.selected_profile, config=config)
        window.show()
        sys.exit(app.exec())
