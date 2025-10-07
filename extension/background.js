// URL logger background service worker (Manifest V3)
// Manual-only: posts current tab URL when the toolbar button is clicked
// or when the in-page floating button requests it via message.

const ENDPOINT = 'http://localhost:8000/ingest';

async function postVisit(url, tabId, source) {
  try {
    const response = await fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url,
        tab_id: tabId,
        timestamp: new Date().toISOString(),
        source,
      }),
    });
    return response.ok;
  } catch (_) {
    return false;
  }
}

// Manual trigger: click the toolbar icon to send current tab URL
chrome.action.onClicked.addListener(async (tab) => {
  const url = tab?.url;
  const tabId = tab?.id;
  if (typeof url === 'string' && (url.startsWith('http://') || url.startsWith('https://'))) {
    const ok = await postVisit(url, tabId, 'manualClick');
    // Visual feedback via badge
    chrome.action.setBadgeText({ text: ok ? '✓' : '✗', tabId });
    chrome.action.setBadgeBackgroundColor({ color: ok ? '#4CAF50' : '#F44336', tabId });
    setTimeout(() => chrome.action.setBadgeText({ text: '', tabId }), 1500);
  }
});

// Manual trigger: message from content script floating button
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.type === 'URL_LOGGER_SEND') {
    const url = typeof message.url === 'string' ? message.url : undefined;
    const tabId = sender?.tab?.id;
    if (url && (url.startsWith('http://') || url.startsWith('https://'))) {
      postVisit(url, tabId, 'inPageButton')
        .then((ok) => sendResponse({ ok }))
        .catch(() => sendResponse({ ok: false }));
    } else {
      sendResponse({ ok: false });
    }
    return true; // keep the channel open for async response
  }
});
