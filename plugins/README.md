# Plugins Directory

Tarium supports simple JavaScript injection plugins.

## How it works

- Put `.js` files in this folder.
- Open Tarium → **Plugins** popup.
- Enable/disable each plugin **per profile**.

Enabled plugin scripts are injected when pages load in that profile.

## Example plugin

Create `plugins/hello_banner.js`:

```js
(() => {
  const id = 'tarium-plugin-banner';
  if (document.getElementById(id)) return;

  const banner = document.createElement('div');
  banner.id = id;
  banner.textContent = 'Hello from Tarium plugin';
  banner.style.cssText = [
    'position:fixed',
    'bottom:12px',
    'right:12px',
    'z-index:999999',
    'padding:8px 10px',
    'border-radius:8px',
    'background:#111',
    'color:#fff',
    'font:12px system-ui',
    'box-shadow:0 2px 8px rgba(0,0,0,.35)'
  ].join(';');

  document.body.appendChild(banner);
})();
```

## Notes

- Keep plugins defensive (check if DOM nodes already exist before inserting).
- Prefer small scripts that fail gracefully on sites with strict CSP.
- Use profile-level toggles to test safely without affecting other profiles.
