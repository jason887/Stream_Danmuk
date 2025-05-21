// static/presenter_dom_vars.js
// Declares global variables to hold references to DOM elements.
// These will be assigned in presenter_init.js after DOMContentLoaded.

// Script Browsing & Loading
let scriptSelect, loadSelectedScriptBtn, scriptPathBreadcrumb, scriptBrowseUpBtn;
let scriptNameSpan, progressSpan, currentEventIndexSpan, totalEventsSpan, currentLineDiv, currentPromptDiv;
let prevEventBtn, nextEventBtn;

// Roast Mode Elements
let roastTargetNameInput, startRoastBtn, advanceRoastBtn, exitRoastBtn, roastStatusDiv;

// Boss Danmaku Elements
let bossNicknameInput, giftNameInput, sendWelcomeBossBtn, sendThanksBossBtn;

// General Danmaku Fetch/Send Elements
let streamerSearchInput, streamerSearchResultsDiv; // Search input and results div
let fetchWelcomeDanmakuBtn, fetchRoastDanmakuBtn, fetchReversalBtn, fetchCaptionsBtn; // Fetch buttons
let danmakuOutputArea; // Common output area for fetched lists
let autoSendDanmakuBtn; // Auto send button for fetched Welcome/Mock

// Status Display Elements (Declared here, assigned in presenter_init.js, used by presenter_core.js and ui_utils)
let statusMessageDiv;
let connectionStatusCircle, connectionStatusCircleFooter, statusTextFooter; // References to status elements

// Feature-specific Global Variables (State variables - minimal, related to UI state)
// Keeping these here as they relate to UI state (which list was last fetched)
let lastFetchedWelcomeDanmaku = []; // Store fetched Welcome danmaku list for auto-send
let lastFetchedRoastDanmaku = []; // Store fetched Mock (Roast) danmaku list for auto-send
let currentStreamerOrTopicName = ""; // Store the name used for the last danmaku/quote fetch

// Assumes sendMessage and updateStatus are exposed globally by presenter_core.js via window.*
// Assumes setMessageHandler is exposed globally by presenter_core.js via window.presenterCore.setMessageHandler

console.log("presenter_dom_vars.js loaded.");
