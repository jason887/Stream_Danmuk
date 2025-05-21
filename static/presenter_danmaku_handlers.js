// static/presenter_danmaku_handlers.js
// Handles WebSocket messages and UI interactions related to all types of danmaku (fetch, display, send).
// Assumes global DOM variables (window.*) are declared in presenter_dom_vars.js.
// Assumes sendMessage and updateStatus (window.*) are available from presenter_core.js.
// Assumes UI utility functions (window.*) are available (clearOutputArea, displayFetchedList, handleCopyOutputArea, disableAutoSendButtons, reEnableAutoSendButtons).
// Access global state variables for fetched lists (declared in presenter_dom_vars.js)
// window.lastFetchedWelcomeDanmaku; // Declared globally in presenter_dom_vars.js
// window.lastFetchedRoamaku;   // Declared globally in presenter_dom_vars.js
// window.currentStreamerOrTopicName; // Declared globally in presenter_dom_vars.js


// --- Handler Functions (Called by Event Listeners or presenter_init.js's dispatcher) ---

// Handles click on "欢迎大哥" or "感谢大哥礼物" buttons.
// type: "welcome_boss" or "thanks_boss_gift".
function handleSendBossDanmaku(type) {
    // Access global vars and check existence
    if (!window.bossNicknameInput || (type === 'thanks_boss_gift' && !window.giftNameInput) || !window.sendWelcomeBossBtn || (type === 'thanks_boss_gift' && !window.sendThanksBossBtn)) {
         console.warn(`Danmaku_Handlers: Missing DOM elements for sending boss danmaku type "${type}".`);
         return;
    }

    const bossName = window.bossNicknameInput.value.trim();
    const giftName = (type === 'thanks_boss_gift' ? window.giftNameInput.value.trim() : "");

    if (!bossName) {
        if (typeof window.updateStatus === 'function') window.updateStatus("发送大哥弹幕需要输入昵称。", "warning");
        window.bossNicknameInput.focus();
        return;
    }

    if (type === 'thanks_boss_gift' && !giftName) {
        if (typeof window.updateStatus === 'function') window.updateStatus("发送感谢大哥礼物弹幕需要输入礼物名称。", "warning");
        window.giftNameInput.focus();
        return;
    }

     // Assumes sendMessage is globally available via window.sendMessage
    if (typeof window.sendMessage === 'function') {
         // Disable buttons while sending (server will also send auto_send_started)
         // Disabling is handled by disableAutoSendButtons helper
        if (typeof window.disableAutoSendButtons === 'function') window.disableAutoSendButtons();
        else console.warn("Danmaku_Handlers: disableAutoSendButtons function not available.");


        const actionData = {
            action: "send_boss_danmaku", // Correct action name expected by server
            danmaku_type: type, // "welcome_boss" or "thanks_boss_gift"
            boss_name: bossName,
            gift_name: giftName
        };

        console.log(`Danmaku_Handlers: Sending action: ${actionData.action} with type "${type}" for "${bossName}" gift "${giftName}".`);
        window.sendMessage(actionData);
        // Server will send 'auto_send_started', 'info' during sending, 'success' or 'error' on completion.
        // 're_enable_auto_send_buttons' will be sent on finish/error/cancel.
    } else {
         console.error("Danmaku_Handlers: sendMessage function not available.");
         if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}


// Handles input in the streamer search input for fuzzy search suggestions.
// Assumes streamerSearchInput and streamerSearchResultsDiv are global.
// Assumes updateStatus, handleGlobalClick, handleSearchResultClick are global utilities.
async function handleStreamerSearchInput() {
    // Access global vars and check existence
    if (!window.streamerSearchInput || !window.streamerSearchResultsDiv) {
         console.warn("Danmaku_Handlers: Missing DOM elements for streamer search.");
         return;
    }

    const term = window.streamerSearchInput.value.trim();
    const resultsDiv = window.streamerSearchResultsDiv;

    // Clear previous results and hide if term is empty
    resultsDiv.innerHTML = '';
    if (!term) {
        resultsDiv.style.display = 'none';
        return;
    }

    // Fetch results from Flask API (This uses fetch API, not WebSocket)
    try {
        // Assumes fetch is available (standard browser API)
        // Use the API endpoint that searches the DB directly
        const response = await fetch(`/api/search_streamer_names?term=${encodeURIComponent(term)}`); // Corrected API endpoint
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const names = await response.json(); // Expecting a list of strings

        if (names && names.length > 0) {
            // Make resultsDiv visible before adding items
            resultsDiv.style.display = 'block'; // Show the results div
            names.forEach(name => {
                const resultItem = document.createElement('div');
                resultItem.classList.add('search-result-item'); // Add class for click delegation (handled in ui_utils)
                resultItem.textContent = name;
                resultsDiv.appendChild(resultItem);
            });
            console.debug(`Danmaku_Handlers: Found ${names.length} search results for term "${term}".`);

        } else {
            // No results found
            resultsDiv.innerHTML = ''; // Clear previous results
            const noResultItem = document.createElement('div');
            noResultItem.textContent = "未找到匹配项";
            noResultItem.style.fontStyle = "italic";
            noResultItem.style.color = "#888";
             noResultItem.style.cursor = "default"; // Not clickable
             noResultItem.style.padding = "8px"; // Match padding
            resultsDiv.appendChild(noResultItem);
            resultsDiv.style.display = 'block'; // Show the results div with "No results"
            console.debug(`Danmaku_Handlers: No search results found for term "${term}".`);
        }

    } catch (error) {
        console.error('Danmaku_Handlers: 搜索主播/主题名称时出错:', error);
        if (typeof window.updateStatus === 'function') {
            window.updateStatus('搜索主播/主题名称时出错，请稍后重试。', 'error');
        }
        if (window.streamerSearchResultsDiv) { // Ensure element exists before hiding
            window.streamerSearchResultsDiv.innerHTML = ''; // Clear results on error
            window.streamerSearchResultsDiv.style.display = 'none'; // Hide on error
        }
    }
}

// Handles click on fetch buttons (Welcome, Roast/Mock, Reversal, Captions).
// type: 'welcome', 'roast', 'reversal', 'captions'.
// Assumes streamerSearchInput, fetch buttons are global.
// Assumes sendMessage, updateStatus, clearOutputArea are global utilities.
// Assumes lastFetchedWelcomeDanmaku, lastFetchedRoastDanmaku, currentStreamerOrTopicName are global state vars.
function handleFetchDanmakuList(type) {
    // Access global vars and check existence
    if (!window.streamerSearchInput || !(window.fetchWelcomeDanmakuBtn || window.fetchRoastDanmakuBtn || window.fetchReversalBtn || window.fetchCaptionsBtn)) {
         console.warn(`Danmaku_Handlers: Missing DOM elements for fetching type "${type}".`);
         return;
    }

    const nameOrTopic = window.streamerSearchInput.value.trim();
    if (!nameOrTopic) {
        const inputLabel = (type === 'captions' ? '主题名' : '主播名');
        if (typeof window.updateStatus === 'function') window.updateStatus(`请输入${inputLabel}进行搜索和获取。`, "warning");
        window.streamerSearchInput.focus();
        return;
    }

    // Store the name/topic for auto-send button reference if it's a type that can be auto-sent
    if (type === 'welcome' || type === 'roast') {
         window.currentStreamerOrTopicName = nameOrTopic;
    } else {
         window.currentStreamerOrTopicName = ""; // Clear for types not auto-sent by that button
    }


     // Assumes sendMessage is globally available via window.sendMessage
    if (typeof window.sendMessage === 'function') {
        const actionMap = {
            'welcome': 'fetch_danmaku_list', // Server handler needs danmaku_type
            'roast': 'fetch_danmaku_list',   // Server handler needs danmaku_type
            'reversal': 'fetch_reversal',    // Server has specific handler
            'captions': 'fetch_captions'     // Server has specific handler
        };
         const action = actionMap[type];
         if (!action) {
              console.error(`Danmaku_Handlers: Unknown fetch type "${type}".`);
              if (typeof window.updateStatus === 'function') window.updateStatus(`内部错误：未知获取类型 "${type}"。`, "error");
              return;
         }

        let messageData = { action: action };
        if (type === 'welcome' || type === 'roast') {
            messageData.streamer_name = nameOrTopic;
            messageData.danmaku_type = type; // Add type for the server handler
        } else if (type === 'reversal') {
             messageData.streamer_name = nameOrTopic; // Reversal uses streamer_name
        } else if (type === 'captions') {
             messageData.topic_name = nameOrTopic; // Captions uses topic_name
        }


        const statusLabel = {
            'welcome': '欢迎弹幕', 'roast': '吐槽弹幕',
            'reversal': '反转语录', 'captions': '主题/段子'
        }[type];

        if (typeof window.updateStatus === 'function') window.updateStatus(`正在获取 ${nameOrTopic} 的${statusLabel}...`, "info");
        // Clear previous results using the utility function
        if (typeof window.clearOutputArea === 'function') window.clearOutputArea();
        else console.warn("Danmaku_Handlers: clearOutputArea function not available.");


        console.log(`Danmaku_Handlers: Sending action: "${action}" for "${nameOrTopic}" (type: ${type}).`);
        window.sendMessage(messageData);

    } else {
         console.error("Danmaku_Handlers: sendMessage function not available.");
         if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}

 // Specific handlers for fetch responses (called by presenter_init.js's dispatcher)
 // Assumes global state variables (lastFetchedWelcomeDanmaku, lastFetchedRoastDanmaku, currentStreamerOrTopicName) are declared.
 // Assumes displayFetchedList is globally available via window.displayFetchedList.
function handleDanmakuListMessage(data) {
     // data.danmaku_list is a list of strings
     // data includes: danmaku_type, streamer_name, danmaku_list, context
    console.log("Danmaku_Handlers: Received danmaku_list:", data);
    // Access global state vars via window
    if (data.danmaku_type === 'welcome') {
        window.lastFetchedWelcomeDanmaku = Array.isArray(data.danmaku_list) ? data.danmaku_list : []; // Ensure it's an array
         // Store the streamer name associated with these lists if not already set by the fetch trigger
         if (!window.currentStreamerOrTopicName) window.currentStreamerOrTopicName = data.streamer_name || "";
        // Display list using the utility function
        if (typeof window.displayFetchedList === 'function') window.displayFetchedList(window.lastFetchedWelcomeDanmaku, `欢迎弹幕 (${data.streamer_name || ''})`);
        else console.warn("Danmaku_Handlers: displayFetchedList function not available.");
    } else if (data.danmaku_type === 'roast') { // Corresponds to Mock_Danmaku
        window.lastFetchedRoastDanmaku = Array.isArray(data.danmaku_list) ? data.danmaku_list : []; // Ensure it's an array
         // Store the streamer name associated with these lists if not already set by the fetch trigger
         if (!window.currentStreamerOrTopicName) window.currentStreamerOrTopicName = data.streamer_name || "";
         // Display list using the utility function
         if (typeof window.displayFetchedList === 'function') window.displayFetchedList(window.lastFetchedRoastDanmaku, `吐槽弹幕 (${data.streamer_name || ''})`, (item, index) => {
             return `(${index + 1}) ${item}`;
         });
         else console.warn("Danmaku_Handlers: displayFetchedList function not available.");
    } else {
         console.warn("Danmaku_Handlers: Received unexpected danmaku_list type:", data.danmaku_type);
         if (typeof window.displayFetchedList === 'function') window.displayFetchedList([], `未知类型弹幕 (${data.danmaku_type})`);
         else console.warn("Danmaku_Handlers: displayFetchedList function not available.");
    }
}

function handleReversalListMessage(data) {
     // data.reversal_list is a list of dictionaries [{"danmaku_part": "...", "read_part": "..."}, ...]
     // data includes: streamer_name, reversal_list, context
     console.log("Danmaku_Handlers: Received reversal_list:", data);
     const reversalList = Array.isArray(data.reversal_list) ? data.reversal_list : []; // Ensure it's an array
     // Store the streamer name associated with this list if not already set
     if (!window.currentStreamerOrTopicName) window.currentStreamerOrTopicName = data.streamer_name || "";

     // Display list using the utility function
     if (typeof window.displayFetchedList === 'function') {
          window.displayFetchedList(reversalList, `反转语录 (${data.streamer_name || ''})`, (item, index) => {
             // Format reversal for display: Show both parts
             // Ensure item is an object and parts are strings
             const danmakuPart = item && typeof item === 'object' ? item.danmaku_part || '' : '';
             const readPart = item && typeof item === 'object' ? item.read_part || '' : '';
             return `(${index + 1}) <strong>弹幕:</strong> ${danmakuPart} <br> <strong>提示:</strong> ${readPart}`;
         });
     } else console.warn("Danmaku_Handlers: displayFetchedList function not available.");
}

function handleCaptionsListMessage(data) {
     // data.captions_list is a list of strings
     // data includes: topic_name, captions_list, context
    console.log("Danmaku_Handlers: Received captions_list:", data);
    const captionsList = Array.isArray(data.captions_list) ? data.captions_list : []; // Ensure it's an array
     // Store the topic name associated with this list if not already set
     if (!window.currentStreamerOrTopicName) window.currentStreamerOrTopicName = data.topic_name || "";

    // Display list using the utility function
    if (typeof window.displayFetchedList === 'function') {
        window.displayFetchedList(captionsList, `主题/段子 (${data.topic_name || ''})`, (item, index) => {
             // Format captions: Just show the string
             return `(${index + 1}) ${item}`;
        });
    } else console.warn("Danmaku_Handlers: displayFetchedList function not available.");
}

 function handleAntiFanQuotesListMessage(data) {
    // data.quotes_list is a list of strings
    // data includes: quotes_list, context
    console.log("Danmaku_Handlers: Received anti_fan_quotes_list:", data);
    const quotesList = Array.isArray(data.quotes_list) ? data.quotes_list : []; // Ensure it's an array
     // Anti-fan quotes don't need an associated name stored for auto-send purposes here (that's roast mode)

     // Display list using the utility function
     if (typeof window.displayFetchedList === 'function') {
         window.displayFetchedList(quotesList, `怼黑粉语录 (共 ${quotesList.length} 条)`, (item, index) => {
             return `(${index + 1}) ${item}`;
        });
     } else console.warn("Danmaku_Handlers: displayFetchedList function not available.");
}


// Handles click on the "自动发送获取的弹幕" button.
// Assumes autoSendDanmakuBtn and streamerSearchInput are global.
// Assumes lastFetchedWelcomeDanmaku, lastFetchedRoastDanmaku, currentStreamerOrTopicName are global state vars.
// Assumes sendMessage, updateStatus, disableAutoSendButtons are global utilities.
function handleAutoSendFetchedDanmaku() {
    // Access global vars and check existence
    if (!window.autoSendDanmakuBtn || !window.streamerSearchInput) {
         console.warn("Danmaku_Handlers: Missing DOM elements for auto sending fetched danmaku.");
         return;
    }

    // Use the stored name from the last fetch, or fallback to current input value
    const streamerName = window.currentStreamerOrTopicName || window.streamerSearchInput.value.trim();

    if (!streamerName) {
        if (typeof window.updateStatus === 'function') window.updateStatus("请先搜索并获取欢迎/吐槽弹幕。", "warning");
        window.streamerSearchInput.focus();
        return;
    }

    // Check if we actually fetched any lists (this check might be slightly redundant if server also checks)
    // Access global state vars via window
    if (window.lastFetchedWelcomeDanmaku.length === 0 && window.lastFetchedRoastDanmaku.length === 0) {
         if (typeof window.updateStatus === 'function') window.updateStatus(`没有为 "${streamerName}" 获取到欢迎或吐槽弹幕，无法自动发送。`, "warning");
         return;
    }


     // Assumes sendMessage is globally available via window.sendMessage
    if (typeof window.sendMessage === 'function') {
        if (typeof window.updateStatus === 'function') window.updateStatus(`正在发送 ${streamerName} 的欢迎/吐槽弹幕...`, "info");
        // Disabling buttons is handled by auto_send_started message from server, calling disableAutoSendButtons helper
        // We can trigger the disable immediately in UI for responsiveness
         if (typeof window.disableAutoSendButtons === 'function') window.disableAutoSendButtons();
         else console.warn("Danmaku_Handlers: disableAutoSendButtons function not available.");


        // Send action to server. Server refetches the lists to ensure fresh data.
        console.log(`Danmaku_Handlers: Sending action: "auto_send_danmaku" for "${streamerName}".`);
        window.sendMessage({
            action: "auto_send_danmaku", // Correct action name expected by server
            streamer_name: streamerName, // Send the streamer name
            // No need to send the lists themselves, server fetches them
        });
         // Server will send 'auto_send_started', then handle steps, then 'auto_send_finished'/'error'
    } else {
         console.error("Danmaku_Handlers: sendMessage function not available.");
         if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}


// Expose handlers globally via window object so they can be called by event listeners (in init.js) or dispatcher (in init.js)
window.handleSendBossDanmaku = handleSendBossDanmaku;
window.handleStreamerSearchInput = handleStreamerSearchInput; // Called by input event listener
// Fetch button handlers
window.handleFetchDanmakuList = handleFetchDanmakuList; // Handles welcome/roast fetch
// Specific fetch handlers
window.handleFetchReversal = handleFetchReversal;
window.handleFetchCaptions = handleFetchCaptions;
// Dispatcher message handlers
window.handleDanmakuListMessage = handleDanmakuListMessage; // Called by init.js dispatcher
window.handleReversalListMessage = handleReversalListMessage; // Called by init.js dispatcher
window.handleCaptionsListMessage = handleCaptionsListMessage; // Called by init.js dispatcher
window.handleAntiFanQuotesListMessage = handleAntiFanQuotesListMessage; // Called by init.js dispatcher
window.handleAutoSendFetchedDanmaku = handleAutoSendFetchedDanmaku; // Called by button click

console.log("presenter_danmaku_handlers.js loaded.");
