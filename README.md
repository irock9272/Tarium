Tarium Browser
==============

Tarium is a small, profile‑based web browser built with **Python** and **PyQt6 WebEngine**.  
It’s designed to be simple, fast to launch, and easy to hack on.

Features
--------

- **Multiple profiles**
  - Separate `profiles/` directory per user/profile.
  - Each profile has its own cookies, history, bookmarks, and enabled plugins.

- **Tabbed browsing**
  - Modern tab strip with a dark theme.
  - Tabs are **reorderable**, and titles/icons always follow the correct tab.

- **Bookmarks & history**
  - Bookmark the current page from the bookmarks popup.
  - Bookmarks update **live** in the dialog when you add/remove them.
  - History dialog shows the most recent entries (double‑click to reopen).

- **Plugins (JS injection)**
  - Drop `.js` files into the `plugins/` folder.
  - Enable/disable them per profile from the **Plugins** popup.

- **Unified dark UI**
  - Consistent dark style across the main window, dialogs, and lists.
  - Custom toolbar icons for navigation, tabs, bookmarks, history, plugins, and a hamburger menu.

- **About dropdown**
  - A **hamburger icon** in the toolbar opens a small dropdown with About info (name, version, copyright).

- **Smart address/search bar**
  - Type a full URL (with or without `http`) → loads that site.
  - Type just a word or phrase (e.g. `youtube`) → opens a **Google search** for that query in the current tab.
  - When on the **home page**, the bar stays empty and just shows its placeholder text.

- **Keyboard shortcuts**
  - `Ctrl+T` → open a new tab.
  - `Ctrl+W` → close the current tab.
  - `Ctrl+1` … `Ctrl+9` → switch to the corresponding tab (ignored if that tab doesn’t exist).

Getting Started
---------------

### Requirements

- Python 3.11+ (matches the `.python-version` / `pyproject.toml` setup)
- A working Qt WebEngine environment (PyQt6‑WebEngine)

All Python dependencies are managed via `uv` (see `pyproject.toml` and `uv.lock`).

### Install dependencies

If you have `uv` installed:

```bash
uv sync
```

Or with plain `pip` (not officially supported, but roughly):

```bash
pip install -e .
```

### Run the browser

From the project root:

```bash
python -m browser
```

On first launch you’ll see the **Profile Manager**, where you can:

- Select an existing profile  
- Create a new profile (it will get its own `browser_data/` directory)  
- Delete a profile

Project Layout
--------------

- `browser.py` – main application window, tabs, dialogs, and all browser logic.
- `main.py` – simple entry point (can be expanded if needed).
- `profiles/` – created at runtime; contains per‑profile data.
- `icons/` – toolbar and UI icons (back, forward, home, new tab, plugins, bookmarks, hamburger menu, etc.).
- `plugins/` – JavaScript files injected into pages for enabled profiles.
- `pyproject.toml` / `uv.lock` – Python project & dependency metadata.

Developer Notes
---------------

- UI styling is centralized in `APP_STYLESHEET` inside `browser.py`.  
  If you want to tweak colors, font sizes, or widget appearance, start there.
- Tabs are managed with a `QTabWidget`; title and icon updates are bound via helpers that  
  always re‑locate the tab by widget reference, so dragging tabs around keeps labels correct.
- The address bar’s behavior (URL vs search) and URL‑bar syncing live in the `WebBrowser` class.
