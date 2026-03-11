"""
Load and merge Lua config from ./config/*.lua.
No defaults: the merged config must provide all required keys.
Returns (config_dict, errors). If errors is non-empty, config is None and the app must exit.
"""

import os
import re

try:
    from lupa import LuaRuntime
except ImportError:
    LuaRuntime = None

CONFIG_DIR = "config"

# Required theme keys; all must be valid hex colors.
REQUIRED_THEME_KEYS = [
    "background",
    "surface",
    "surface_hover",
    "surface_pressed",
    "text",
    "list_bg",
    "tab_bg",
    "tab_selected",
    "tab_hover",
]


def _lua_table_to_python(obj):
    """Recursively convert a Lua table (from lupa) to Python dict/list."""
    if obj is None:
        return None
    try:
        if hasattr(obj, "keys"):
            keys = list(obj.keys())
        elif hasattr(obj, "__getitem__") and hasattr(obj, "__iter__"):
            keys = list(obj)
        else:
            return obj
        if not keys:
            return {}
        try:
            int_keys = [int(k) for k in keys]
            if int_keys == list(range(1, len(int_keys) + 1)):
                return [_lua_table_to_python(obj[i]) for i in range(1, len(int_keys) + 1)]
        except (ValueError, TypeError, KeyError):
            pass
        return {str(k): _lua_table_to_python(obj[k]) for k in keys}
    except Exception:
        pass
    return obj


def _run_lua_file(runtime, path: str) -> tuple[dict | None, str | None]:
    """Execute a Lua file and return (config_dict, error_message)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        return None, f"Could not read {path}: {e}"
    wrapped = "_G._config_result = (function()\n" + content + "\nend)()"
    try:
        runtime.execute(wrapped)
        result = runtime.globals()._config_result
    except Exception as e:
        return None, f"{os.path.basename(path)}: {e}"
    if result is None:
        return {}, None
    return _lua_table_to_python(result), None


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _is_hex_color(s) -> bool:
    s = str(s) if s is not None else ""
    if len(s) < 4:
        return False
    return bool(re.match(r"^#[0-9A-Fa-f]{3,8}$", s))


def _validate_config(merged: dict) -> list[str]:
    """Return a list of validation errors. Empty means valid."""
    errors: list[str] = []

    theme = merged.get("theme")
    if not isinstance(theme, dict):
        errors.append("config: missing or invalid 'theme' (must be a table).")
    else:
        for key in REQUIRED_THEME_KEYS:
            if key not in theme:
                errors.append(f"theme: missing key '{key}'.")
            elif not _is_hex_color(theme[key]):
                errors.append(f"theme: '{key}' must be a hex color (e.g. '#2E2E2E').")

    home_url = merged.get("home_url")
    if home_url is None or not str(home_url).strip().startswith("http"):
        errors.append("config: 'home_url' must be a string starting with http:// or https://.")

    search = merged.get("search")
    if not isinstance(search, dict):
        errors.append("config: 'search' must be a table.")
    else:
        template = search.get("template")
        if template is None or "${query}" not in str(template):
            errors.append("config: 'search.template' must be a string containing '${query}'.")

    keybinds = merged.get("keybinds")
    if keybinds is not None:
        if not isinstance(keybinds, dict):
            errors.append("config: 'keybinds' must be a table.")
        else:
            valid_actions = {"new_tab", "close_tab"}
            valid_actions |= {f"switch_tab_{i}" for i in range(1, 10)}
            for seq, action in keybinds.items():
                seq = str(seq).strip()
                if not seq:
                    errors.append("keybinds: key sequence cannot be empty.")
                    continue
                if isinstance(action, str):
                    if action not in valid_actions:
                        errors.append(f"keybinds['{seq}']: unknown action '{action}'.")
                elif isinstance(action, dict):
                    act = action.get("action")
                    url = action.get("url")
                    if act not in ("new_tab_url", "replace_tab_url"):
                        errors.append(f"keybinds['{seq}']: action must be 'new_tab_url' or 'replace_tab_url'.")
                    elif not isinstance(url, str) or not str(url).strip().startswith("http"):
                        errors.append(f"keybinds['{seq}']: 'url' must be a string starting with http:// or https://.")
                else:
                    errors.append(f"keybinds['{seq}']: value must be an action string or {{action=..., url=...}}.")

    return errors


def load_config() -> tuple[dict | None, list[str]]:
    """
    Load all .lua files from CONFIG_DIR, merge, validate.
    Returns (config_dict or None, list_of_errors).
    If errors is non-empty, config is None and the app should show a fatal error and exit.
    """
    errors: list[str] = []
    merged: dict = {
        "theme": {},
        "home_url": None,
        "search": {},
        "keybinds": {},
    }

    if LuaRuntime is None:
        errors.append("lupa is not installed; cannot load config.")
        return None, errors

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_DIR)
    if not os.path.isdir(config_path):
        errors.append(f"Config directory not found: {CONFIG_DIR}/")
        return None, errors

    lua_files = sorted(f for f in os.listdir(config_path) if f.endswith(".lua"))
    if not lua_files:
        errors.append(f"No .lua files found in {CONFIG_DIR}/")
        return None, errors

    runtime = LuaRuntime()
    for name in lua_files:
        path = os.path.join(config_path, name)
        if not os.path.isfile(path):
            continue
        data, err = _run_lua_file(runtime, path)
        if err:
            errors.append(err)
            continue
        if data:
            if isinstance(data.get("theme"), dict):
                _deep_merge(merged["theme"], data["theme"])
            hu = data.get("home_url")
            if hu is not None:
                hu = str(hu).strip()
                if hu.startswith("http"):
                    merged["home_url"] = hu
            search_data = data.get("search")
            if isinstance(search_data, dict):
                tmpl = search_data.get("template")
                if tmpl is not None:
                    merged["search"]["template"] = str(tmpl)
            keybinds_data = data.get("keybinds")
            if isinstance(keybinds_data, dict):
                for k, v in keybinds_data.items():
                    merged["keybinds"][str(k)] = v

    validation_errors = _validate_config(merged)
    errors.extend(validation_errors)
    if errors:
        return None, errors
    return merged, []


def build_stylesheet(theme: dict) -> str:
    """Build Qt stylesheet from theme. Expects all REQUIRED_THEME_KEYS to be present."""
    t = {k: str(v) for k, v in theme.items()}
    return f"""
    QMainWindow {{ background-color: {t['background']}; }}
    QDialog {{ background-color: {t['background']}; }}
    QLabel {{
        color: {t['text']};
        font-size: 14px;
    }}
    QLineEdit {{
        border-radius: 5px;
        padding: 5px;
        background-color: {t['surface']};
        color: {t['text']};
        font-size: 14px;
    }}
    QPushButton {{
        background-color: {t['surface']};
        color: {t['text']};
        border: 2px solid {t['surface_hover']};
        border-radius: 5px;
        padding: 5px 10px;
    }}
    QPushButton:hover {{ background-color: {t['surface_hover']}; }}
    QPushButton:pressed {{ background-color: {t['surface_pressed']}; }}
    QListWidget {{
        background-color: {t['list_bg']};
        color: {t['text']};
        border-radius: 5px;
    }}
    QTabBar::tab {{
        background-color: {t['tab_bg']};
        color: {t['text']};
        padding: 10px 10px;
        font-size: 14px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }}
    QTabBar::tab:selected {{
        background-color: {t['tab_selected']};
    }}
    QTabBar::tab:hover {{
        background-color: {t['tab_hover']};
    }}
    """
