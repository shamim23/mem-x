Minimal Chrome Extension (MV3) — URL Logger

What it does

- Listens for page loads and SPA URL changes.
- Sends `{ url, tab_id, timestamp, source }` to `http://localhost:8000/ingest`.

Install (Chrome / Edge)

- Build/run the backend first (see `backend/README.md`).
- Open `chrome://extensions/`.
- Enable "Developer mode" (top right).
- Click "Load unpacked" and select the `extension` folder.
- Browse the web; the extension will POST URLs to the backend.

Notes

- The backend URL is hardcoded in `background.js` as `http://localhost:8000/ingest`.
- Update that constant if your backend runs elsewhere.
- Requires permissions: `webNavigation`, `host_permissions: <all_urls>`.

