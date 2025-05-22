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

// --- "怼黑粉" (Counter Black Fans) Single Action Feature ---

// Called when the "获取怼黑粉语录" button is clicked.
function handleFetchAntiFanQuotesRequest() {
    if (typeof window.sendMessage === 'function') {
        if (typeof window.updateStatus === 'function') window.updateStatus("正在获取怼黑粉语录...", "info");
        if (typeof window.clearOutputArea === 'function') window.clearOutputArea(); // Clear previous results

        console.log("Danmaku_Handlers: Sending action: fetch_anti_fan_quotes");
        window.sendMessage({ action: "fetch_anti_fan_quotes" }); 
        // Server will respond with "anti_fan_quotes_list"
    } else {
        console.error("Danmaku_Handlers: sendMessage function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}

function handleAntiFanQuotesListMessage(data) {
    // data.quotes_list is a list of strings (should be 3 quotes)
    // data includes: quotes_list, context
    console.log("Danmaku_Handlers: Received anti_fan_quotes_list:", data);
    const quotesList = Array.isArray(data.quotes_list) ? data.quotes_list : []; 

    if (typeof window.displayFetchedList === 'function') {
        window.displayFetchedList(
            quotesList, 
            `选择一条怼黑粉语录发送 (共 ${quotesList.length} 条):`, 
            (item, index) => { // itemFormatter
                return `(${index + 1}) ${item}`; // Simple numbered list
            },
            (quoteText, originalItem) => { // onItemClick callback
                // quoteText is the selected quote string
                sendSelectedAntiFanQuoteToAudience(quoteText);
            }
        );
    } else {
        console.warn("Danmaku_Handlers: displayFetchedList function not available.");
    }
    // Status update is handled by displayFetchedList
}

// Called when a presenter clicks on a fetched anti-fan quote.
function sendSelectedAntiFanQuoteToAudience(quoteText) {
    if (!quoteText || typeof quoteText !== 'string') {
        console.warn("Danmaku_Handlers: Invalid quote text for sending to audience.");
        if (typeof window.updateStatus === 'function') window.updateStatus("无法发送无效的怼黑粉语录。", "warning");
        return;
    }

    if (typeof window.sendMessage === 'function') {
        const messageData = {
            action: "send_selected_anti_fan_quote_to_audience",
            quote_text: quoteText
        };
        console.log("Danmaku_Handlers: Sending action: send_selected_anti_fan_quote_to_audience", messageData);
        window.sendMessage(messageData);
        if (typeof window.updateStatus === 'function') window.updateStatus(`已发送怼黑粉语录: "${quoteText}" 给观众`, "success");
    } else {
        console.error("Danmaku_Handlers: sendMessage function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化，无法发送。", "error");
    }
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
window.handleFetchAntiFanQuotesRequest = handleFetchAntiFanQuotesRequest; // Called by button click in presenter_init.js
// sendSelectedAntiFanQuoteToAudience is an internal callback, no need to expose on window directly.
window.handleAutoSendFetchedDanmaku = handleAutoSendFetchedDanmaku; // Called by button click


// --- "欢迎大哥" (Welcome Big Brother) Specific Feature ---

// Called when the "发送欢迎大哥弹幕" button is clicked.
function handleSendWelcomeBigBrotherRequest() {
    if (!window.bigBrotherNameInput || !window.sendWelcomeBigBrotherBtn) {
        console.warn("Danmaku_Handlers: Missing DOM elements for 'Welcome Big Brother' feature.");
        if (typeof window.updateStatus === 'function') window.updateStatus("欢迎大哥功能UI元素未找到，请刷新。", "error");
        return;
    }

    let bigBrotherName = window.bigBrotherNameInput.value.trim();
    if (!bigBrotherName) {
        bigBrotherName = "大哥"; // Default name if input is empty
        if (typeof window.updateStatus === 'function') window.updateStatus("大哥昵称为空，已使用默认昵称“大哥”。", "info");
        // window.bigBrotherNameInput.value = bigBrotherName; // Optionally update the input field
    }

    if (typeof window.sendMessage === 'function') {
        if (typeof window.updateStatus === 'function') window.updateStatus(`正在为 ${bigBrotherName} 发送欢迎弹幕...`, "info");
        
        // Disable button to prevent multiple clicks while processing
        window.sendWelcomeBigBrotherBtn.disabled = true;

        const messageData = {
            action: "fetch_big_brother_welcome", // Matches backend handler
            big_brother_name: bigBrotherName
        };

        console.log("Danmaku_Handlers: Sending action: fetch_big_brother_welcome", messageData);
        window.sendMessage(messageData);
        // Server will respond with success/error, and broadcast to audience.
        // Presenter button will be re-enabled via re_enable_auto_send_buttons from server if it's part of that flow,
        // or we might need a specific success/error message from server to re-enable it here.
        // For now, let's assume re_enable_auto_send_buttons will cover it or do it manually on response.
        // The backend currently sends "bb_welcome_sent" or error.
        // We should re-enable the button in the message handler for these specific messages.
    } else {
        console.error("Danmaku_Handlers: sendMessage function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}

// Expose the new handler for the button click
window.handleSendWelcomeBigBrotherRequest = handleSendWelcomeBigBrotherRequest;


// --- "感谢大哥礼物" (Thank Big Brother for Gift) Feature ---

// Called when the "发送感谢大哥礼物弹幕" button is clicked.
function handleSendGiftThanksRequest() {
    if (!window.giftThanksBigBrotherNameInput || !window.giftThanksGiftNameInput || !window.sendGiftThanksBtn) {
        console.warn("Danmaku_Handlers: Missing DOM elements for 'Thank Big Brother for Gift' feature.");
        if (typeof window.updateStatus === 'function') window.updateStatus("感谢大哥礼物功能UI元素未找到，请刷新。", "error");
        return;
    }

    let bigBrotherName = window.giftThanksBigBrotherNameInput.value.trim();
    let giftName = window.giftThanksGiftNameInput.value.trim();

    if (!bigBrotherName) {
        bigBrotherName = "大哥"; // Default name
        if (typeof window.updateStatus === 'function') window.updateStatus("大哥昵称为空，已使用默认昵称“大哥”。", "info");
    }
    if (!giftName) {
        giftName = "礼物"; // Default gift name
        if (typeof window.updateStatus === 'function') window.updateStatus("礼物名称为空，已使用默认名称“礼物”。", "info");
    }

    if (typeof window.sendMessage === 'function') {
        if (typeof window.updateStatus === 'function') window.updateStatus(`正在为 ${bigBrotherName} 的 ${giftName} 发送感谢弹幕...`, "info");
        
        window.sendGiftThanksBtn.disabled = true; // Disable button

        const messageData = {
            action: "fetch_gift_thanks_danmaku", // Matches backend handler
            big_brother_name: bigBrotherName,
            gift_name: giftName
        };

        console.log("Danmaku_Handlers: Sending action: fetch_gift_thanks_danmaku", messageData);
        window.sendMessage(messageData);
        // Server will respond with success/error and broadcast to audience.
        // Button re-enable logic will be similar to Welcome Big Brother.
    } else {
        console.error("Danmaku_Handlers: sendMessage function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}

// Expose the new handler for the button click
window.handleSendGiftThanksRequest = handleSendGiftThanksRequest;


// --- "欢迎吐槽" (Welcome Complaints) Feature ---

function handleFetchComplaintsDanmaku() {
    // Access global DOM elements via window
    if (!window.reversedAnchorNameInput || !window.themeEventNameInput || !window.confirmComplaintsBtn) {
        console.warn("Danmaku_Handlers: Missing DOM elements for 'Welcome Complaints' feature.");
        if (typeof window.updateStatus === 'function') window.updateStatus("吐槽功能UI元素未找到，请刷新。", "error");
        return;
    }

    const reversedAnchorName = window.reversedAnchorNameInput.value.trim();
    const themeEventName = window.themeEventNameInput.value.trim();

    if (!reversedAnchorName && !themeEventName) {
        if (typeof window.updateStatus === 'function') window.updateStatus("请输入反转主播名或主题/事件名中的至少一个。", "warning");
        // Optionally focus the first empty field
        if (!reversedAnchorName) window.reversedAnchorNameInput.focus();
        else window.themeEventNameInput.focus();
        return;
    }

    if (typeof window.sendMessage === 'function') {
        if (typeof window.updateStatus === 'function') window.updateStatus("正在获取吐槽弹幕...", "info");
        if (typeof window.clearOutputArea === 'function') window.clearOutputArea(); // Clear previous results

        const messageData = {
            action: "fetch_complaints_danmaku",
            reversed_anchor_name: reversedAnchorName,
            theme_event_name: themeEventName
        };

        console.log("Danmaku_Handlers: Sending action: fetch_complaints_danmaku", messageData);
        window.sendMessage(messageData);
        // Server should respond with a message like 'complaints_danmaku_list' or 'error'
    } else {
        console.error("Danmaku_Handlers: sendMessage function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}

// Handler for receiving complaints danmaku list from the server
function handleComplaintsDanmakuListMessage(data) {
    // data expected to have: complaints_list (array of strings/objects), context
    console.log("Danmaku_Handlers: Received complaints_danmaku_list:", data);
    const complaintsList = Array.isArray(data.complaints_list) ? data.complaints_list : [];

    // Display list using the utility function, similar to other lists
    if (typeof window.displayFetchedList === 'function') {
        window.displayFetchedList(
            complaintsList, 
            `综合吐槽结果 (共 ${complaintsList.length} 条)`, 
            (item, index) => { // itemFormatter
                // The item is already formatted like "[来源] 内容" by the backend.
                // We can just display it, or add numbering.
                return `(${index + 1}) ${item}`;
            },
            (commentText, originalItem) => { // onItemClick callback
                // commentText here is the extracted text part (e.g., "内容")
                // originalItem is the full string like "[来源] 内容"
                sendSelectedComplaintToAudience(commentText, originalItem);
            }
        );
    } else {
        console.warn("Danmaku_Handlers: displayFetchedList function not available.");
    }

    // The status update is now part of displayFetchedList's success message.
    // if (data.message && typeof window.updateStatus === 'function') {
    //     window.updateStatus(data.message, data.status_type || "info");
    // }
}

// New function to send the selected complaint to the audience
function sendSelectedComplaintToAudience(commentText, originalItem) {
    if (!commentText || typeof commentText !== 'string') {
        console.warn("Danmaku_Handlers: Invalid comment text for sending to audience.");
        if (typeof window.updateStatus === 'function') window.updateStatus("无法发送无效的吐槽评论。", "warning");
        return;
    }

    if (typeof window.sendMessage === 'function') {
        const messageData = {
            action: "send_selected_complaint_to_audience",
            comment_text: commentText,
            original_item: originalItem // Send the original item too for context if needed by server/audience
        };
        console.log("Danmaku_Handlers: Sending action: send_selected_complaint_to_audience", messageData);
        window.sendMessage(messageData);
        if (typeof window.updateStatus === 'function') window.updateStatus(`已发送吐槽: "${commentText}" 给观众`, "success");
    } else {
        console.error("Danmaku_Handlers: sendMessage function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化，无法发送。", "error");
    }
}


// Expose new handlers globally
window.handleFetchComplaintsDanmaku = handleFetchComplaintsDanmaku;
window.handleComplaintsDanmakuListMessage = handleComplaintsDanmakuListMessage;
// sendSelectedComplaintToAudience is not directly called by event listeners or dispatcher, so no need to expose on window.

console.log("presenter_danmaku_handlers.js loaded.");
