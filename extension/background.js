// Minimal URL logger background service worker (Manifest V3)
// Posts visited URLs to a local FastAPI backend.

const ENDPOINT = 'http://localhost:8000/ingest';

async function postVisit(url, tabId, source) {
  try {
    await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        tab_id: tabId,
        timestamp: new Date().toISOString(),
        source,
      }),
    });
  } catch (e) {
    // Swallow errors; backend may be offline.
  }
}

// Capture full page loads
chrome.webNavigation.onCompleted.addListener(
  (details) => {
    if (details && details.frameId === 0 && details.url) {
      postVisit(details.url, details.tabId, 'onCompleted');
    }
  },
  { url: [{ schemes: ['http', 'https'] }] }
);

// Capture SPA URL changes (history.pushState / replaceState)
chrome.webNavigation.onHistoryStateUpdated.addListener(
  (details) => {
    if (details && details.frameId === 0 && details.url) {
      postVisit(details.url, details.tabId, 'onHistoryStateUpdated');
    }
  },
  { url: [{ schemes: ['http', 'https'] }] }
);

