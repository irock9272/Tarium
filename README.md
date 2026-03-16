# Tarium Browser

Tarium is a lightweight, profile-based browser built with **Python + PyQt6 WebEngine**.

This README now stays intentionally short.
Directory-specific details live in local READMEs:

- [`config/README.md`](config/README.md) — Lua config schema, required keys, examples.
- [`plugins/README.md`](plugins/README.md) — JavaScript plugin format and usage.
- [`profiles/README.md`](profiles/README.md) — profile data layout and behavior.
- [`icons/README.md`](icons/README.md) — icon asset usage and naming notes.

## Quick Start

### Install

```bash
uv sync
```

(Alternative)

```bash
pip install -e .
```

### Run

```bash
python -m browser
```

On first launch, use the **Profile Manager** to create or select a profile.

## What you get

- Isolated per-profile browser data.
- Reorderable tabs, bookmarks/history dialogs, and configurable keybinds.
- Lua-based customization for theme/home/search.
- Optional per-profile JavaScript plugin injection.

## Repository Map

- `browser.py` — main browser window + UI logic
- `config_loader.py` — loads/merges Lua config
- `main.py` — entrypoint
- `config/` — Lua config files and config docs
- `plugins/` — user JS plugins and plugin docs
- `profiles/` — runtime profile data and profile docs
- `icons/` — image assets and icon docs

## Requirements

- Python **3.11+**
- `PyQt6-WebEngine` runtime dependencies available on your system

Dependencies are pinned in `uv.lock` and defined in `pyproject.toml`.
