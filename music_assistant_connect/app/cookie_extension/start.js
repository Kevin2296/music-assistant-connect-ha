chrome.runtime.onInstalled.addListener(()=>chrome.tabs.create({url:chrome.runtime.getURL('bridge.html'),active:false}));
