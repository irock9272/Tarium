# Tarium Browser — Config (Lua)

All `.lua` files in this folder are run at startup and their returned tables are **merged** (later files override earlier for the same keys). You must provide a complete config; there are no built-in defaults. If any file fails to load or the merged config is invalid, the browser shows a **fatal error** and exits.

---

## Required keys

The merged config must define all of the following. You can split them across files (e.g. `theme.lua` and `web.lua`).

### `theme` (table)

All values must be **hex colors** (e.g. `"#2E2E2E"`).

| Key             | Description                          |
|-----------------|--------------------------------------|
| `background`    | Main window and dialog background    |
| `surface`       | Buttons, inputs, tab bar base        |
| `surface_hover` | Button/input hover, border accent   |
| `surface_pressed` | Button pressed state              |
| `text`          | Label and input text                |
| `list_bg`       | List widgets (e.g. bookmarks, history) |
| `tab_bg`        | Tab background                       |
| `tab_selected`  | Selected tab                         |
| `tab_hover`     | Tab hover                            |

### `home_url` (string)

The URL loaded for “Home” and for new tabs. Must start with `http://` or `https://`.

### `search` (table)

Must contain:

| Key        | Description |
|------------|-------------|
| `template` | URL template for the search bar. Must include the literal **`${query}`**, which is replaced by the user’s search text (e.g. `"https://www.google.com/search?q=${query}"`). |

### `keybinds` (table, optional)

Maps key sequences to actions. If omitted, no keyboard shortcuts are registered.

**Key:** A string key sequence (e.g. `"Ctrl+T"`, `"Ctrl+Shift+H"`).

**Value:** Either a string action or a table for URL actions.

| Action string    | Description                    |
|------------------|--------------------------------|
| `new_tab`        | Open a new tab (home page)     |
| `close_tab`      | Close the current tab          |
| `switch_tab_1` … `switch_tab_9` | Switch to that tab index |

**URL actions** (table): `{ action = "...", url = "https://..." }`

| Action           | Description                          |
|------------------|--------------------------------------|
| `new_tab_url`    | Open a new tab and load the URL      |
| `replace_tab_url`| Navigate the current tab to the URL  |

Example:

```lua
keybinds = {
  ["Ctrl+T"] = "new_tab",
  ["Ctrl+W"] = "close_tab",
  ["Ctrl+1"] = "switch_tab_1",
  ["Ctrl+Shift+G"] = { action = "new_tab_url", url = "https://www.google.com" },
  ["Ctrl+Shift+D"] = { action = "replace_tab_url", url = "https://duckduckgo.com" },
}
```

---

## Example: minimal setup

**theme.lua**

```lua
return {
  theme = {
    background = "#2E2E2E",
    surface = "#444",
    surface_hover = "#555",
    surface_pressed = "#666",
    text = "#FFFFFF",
    list_bg = "#3A3A3A",
    tab_bg = "#444",
    tab_selected = "#555",
    tab_hover = "#555",
  },
}
```

**web.lua**

```lua
return {
  home_url = "https://online.bonjourr.fr/",
  search = {
    template = "https://www.google.com/search?q=${query}",
  },
}
```

**keybinds.lua** (optional; see `keybinds.lua` in this folder for the standard set)

```lua
return {
  keybinds = {
    ["Ctrl+T"] = "new_tab",
    ["Ctrl+W"] = "close_tab",
    ["Ctrl+1"] = "switch_tab_1",
    -- ...
  },
}
```

---

## Optional: logic

You can use normal Lua (time, random, etc.) and still return a single table at the end. Example: pick one of two themes at random:

```lua
local themes = {
  { background = "#1e1e1e", surface = "#444", ... },
  { background = "#101820", surface = "#333", ... },
}
math.randomseed(os.time())
local chosen = themes[math.random(1, 2)]
return { theme = chosen, home_url = "...", search = { template = "..." } }
```

If anything in your script throws or returns an invalid value, the browser will show a fatal error and exit.
