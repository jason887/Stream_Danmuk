// static/presenter_ui_utils.js
// Contains general UI utility functions used across different feature modules.
// Assumes global DOM variables (window.*) are declared in presenter_dom_vars.js
// and assigned in presenter_init.js.
// Assumes sendMessage and updateStatus (window.*) are available from presenter_core.js.

// --- Utility Functions for UI Control (Enable/Disable Buttons) ---
// These functions manipulate the disabled/visibility state of UI elements.
// They check for element existence before operating.

// Updates the disabled state of the load script button based on selection.
function updateLoadButtonState() {
    if (window.loadSelectedScriptBtn && window.scriptSelect) { // Access global vars via window
       const selectedOption = window.scriptSelect.options[window.scriptSelect.selectedIndex];
       // Enable if an option is selected AND it's not a directory AND not in roast mode
       // Roast mode disabled state is handled by reEnableAutoSendButtons
       window.loadSelectedScriptBtn.disabled = !selectedOption || selectedOption.value === "" || selectedOption.dataset.is_dir === 'true' ;
        console.debug("UI_Utils: Load button state updated.");
    } else {
         console.warn("UI_Utils: loadSelectedScriptBtn or scriptSelect element not found for updateLoadButtonState.");
    }
}

// Disables buttons typically involved in auto-sending or modal sequences.
function disableAutoSendButtons() {
   console.log("UI_Utils: disableAutoSendButtons called.");
    // Disable auto-send related buttons
    if (window.autoSendDanmakuBtn) window.autoSendDanmakuBtn.disabled = true;
    if (window.sendWelcomeBossBtn) window.sendWelcomeBossBtn.disabled = true;
    if (window.sendThanksBossBtn) window.sendThanksBossBtn.disabled = true;

    // Also disable roast start button
    if (window.startRoastBtn) window.startRoastBtn.disabled = true;
    if (window.roastTargetNameInput) window.roastTargetNameInput.disabled = true; // Disable roast input

    // Disable script navigation/browsing when auto-sending or in modal mode
    disableNavigationButtons(); // Calls helper defined here
    disableScriptBrowse();      // Calls helper defined here

    // Disable fetch buttons and search input?
    if (window.fetchWelcomeDanmakuBtn) window.fetchWelcomeDanmakuBtn.disabled = true;
    if (window.fetchRoastDanmakuBtn) window.fetchRoastDanmakuBtn.disabled = true;
    if (window.fetchReversalBtn) window.fetchReversalBtn.disabled = true;
    if (window.fetchCaptionsBtn) window.fetchCaptionsBtn.disabled = true;
    if (window.streamerSearchInput) window.streamerSearchInput.disabled = true; // Disable search input too
    if (window.streamerSearchResultsDiv) window.streamerSearchResultsDiv.style.display = 'none'; // Hide search results
    console.debug("UI_Utils: AutoSend/Modal controls disabled.");
}

// Function to re-enable relevant auto-send/modal buttons after a task finishes or errors.
// Called by the 're_enable_auto_send_buttons' message from the server/core or by core on disconnect/error.
// This is a crucial function for resetting UI state after modal operations.
function reEnableAutoSendButtons() {
   console.log("UI_Utils: reEnableAutoSendButtons called.");
   // Re-enable general auto-send button
   if (window.autoSendDanmakuBtn) window.autoSendDanmakuBtn.disabled = false;
   // Re-enable Boss danmaku buttons
   if (window.sendWelcomeBossBtn) window.sendWelcomeBossBtn.disabled = false;
   if (window.sendThanksBossBtn) window.sendThanksBossBtn.disabled = false;

   // Re-enable roast start button IF roast sequence is NOT currently active
    // Roast sequence is active if advanceRoastBtn is visible (check style.display)
    if (window.startRoastBtn) {
        if (window.advanceRoastBtn && window.advanceRoastBtn.style.display === 'none') {
            window.startRoastBtn.disabled = false;
            if (window.roastTargetNameInput) window.roastTargetNameInput.disabled = false; // Re-enable roast input
        } else {
             // If roast mode is active, start button stays disabled
            window.startRoastBtn.disabled = true;
            if (window.roastTargetNameInput) window.roastTargetNameInput.disabled = true;
        }
    }
    // Advance and Exit roast buttons are enabled/disabled by the roast handlers themselves (presenter_roast_handlers.js)

   // Re-enable script navigation/browsing IF roast sequence is NOT currently active
    // Check roast mode by advanceRoastBtn visibility
    if (window.advanceRoastBtn && window.advanceRoastBtn.style.display === 'none') {
       reEnableNavigationButtons(); // Calls helper defined here (which calls sendMessage)
       reEnableScriptBrowse(); // Calls helper defined here (which calls sendMessage)
    } else {
        // If roast mode is active, ensure script navigation/browsing stays disabled
        disableNavigationButtons(); // Calls helper defined here
        disableScriptBrowse();      // Calls helper defined here
    }


    // Re-enable fetch buttons and search input
    if (window.fetchWelcomeDanmakuBtn) window.fetchWelcomeDanmakuBtn.disabled = false;
    if (window.fetchRoastDanmakuBtn) window.fetchRoastDanmakuBtn.disabled = false;
    if (window.fetchReversalBtn) window.fetchReversalBtn.disabled = false;
    if (window.fetchCaptionsBtn) window.fetchCaptionsBtn.disabled = false;
    if (window.streamerSearchInput) window.streamerSearchInput.disabled = false; // Enable search input
   // Search results div state is managed by handleStreamerSearchInput and handleGlobalClick
   console.debug("UI_Utils: AutoSend/Modal controls re-enabled.");
}

// Disables script navigation buttons.
function disableNavigationButtons() {
   if (window.prevEventBtn) window.prevEventBtn.disabled = true;
   if (window.nextEventBtn) window.nextEventBtn.disabled = true;
    console.debug("UI_Utils: Navigation buttons disabled.");
}

// Re-enables navigation buttons by requesting state sync from the server.
// Assumes sendMessage is globally available via window.sendMessage.
function reEnableNavigationButtons() {
    // Request current state to sync UI
    // Assumes sendMessage is globally available via window.sendMessage
    if (typeof window.sendMessage === 'function') {
         console.log("UI_Utils: Requesting state sync to re-enable navigation buttons.");
         window.sendMessage({action: "get_current_state"}); // This triggers current_event_update message
         // The current_event_update handler (in script_handlers.js) will then correctly enable/disable based on index/total
    } else {
         console.error("UI_Utils: sendMessage function not available for reEnableNavigationButtons.");
         // As a fallback, try to enable elements directly if sendMessage is missing, but state might be wrong
         if (window.prevEventBtn) window.prevEventBtn.disabled = false;
         if (window.nextEventBtn) window.nextEventBtn.disabled = false;
    }
}

// Disables script browsing controls.
function disableScriptBrowse() {
   if (window.scriptSelect) window.scriptSelect.disabled = true;
   if (window.loadSelectedScriptBtn) window.loadSelectedScriptBtn.disabled = true; // Ensure load button is disabled too
   if (window.scriptBrowseUpBtn) window.scriptBrowseUpBtn.disabled = true;
    console.debug("UI_Utils: Script browse controls disabled.");
}

// Re-enables script browsing controls by requesting script options from the server.
// Assumes sendMessage is globally available via window.sendMessage.
function reEnableScriptBrowse() {
    // Request current dir listing to sync UI
    // Assumes sendMessage is globally available via window.sendMessage
    if (typeof window.sendMessage === 'function') {
        console.log("UI_Utils: Requesting script options to re-enable browse controls.");
        window.sendMessage({action: "browse_scripts", path: "."}); // Request current dir listing
        // The script_options_update handler (in script_handlers.js) will then correctly enable/disable based on path/options
    } else {
         console.error("UI_Utils: sendMessage function not available for reEnableScriptBrowse.");
         // As a fallback, try to enable elements directly if sendMessage is missing
          if (window.scriptSelect) window.scriptSelect.disabled = false;
          if (window.loadSelectedScriptBtn) updateLoadButtonState(); // Re-evaluate based on selection
          // browse up button state depends on path, hard to determine without server state
          if (window.scriptBrowseUpBtn) { /* Keep disabled or try to infer path? */ }
    }
}

// --- Output Area Helpers ---
// These functions manipulate the common output area.
// Assumes danmakuOutputArea is globally available via window.danmakuOutputArea.

// Clears the content of the output area.
function clearOutputArea() {
   if (window.danmakuOutputArea) { // Check element exists
       window.danmakuOutputArea.innerHTML = '';
       window.danmakuOutputArea.classList.remove('copyable'); // Remove copyable class
       window.danmakuOutputArea.textContent = "请先搜索并选择主播/主题，然后获取弹幕/语录。"; // Reset text
        console.debug("UI_Utils: Output area cleared.");
   } else {
        console.warn("UI_Utils: danmakuOutputArea element not found for clearOutputArea.");
   }
}

// Displays a list of items in the output area with optional formatting.
// list: Array of items (strings or objects).
// title: String, title for the list (e.g., "欢迎弹幕").
// itemFormatter: Optional function (item, index) => string, to format each item's HTML.
// Assumes updateStatus is globally available via window.updateStatus.
function displayFetchedList(list, title, itemFormatter) {
    if (!window.danmakuOutputArea) { // Check element exists
        console.warn("UI_Utils: danmakuOutputArea element not found for displayFetchedList.");
        return;
    }

   window.danmakuOutputArea.innerHTML = ''; // Clear previous content
   // Add copyable class only if there's data
   if (list && list.length > 0) {
       window.danmakuOutputArea.classList.add('copyable'); // Make area copyable
   } else {
       window.danmakuOutputArea.classList.remove('copyable'); // Not copyable if empty
   }


   if (!list || list.length === 0) {
       window.danmakuOutputArea.textContent = `${title} 未找到或为空。`;
       if (typeof window.updateStatus === 'function') window.updateStatus(`${title} 未找到或为空。`, "warning");
        console.debug(`UI_Utils: No list items found for "${title}".`);
       return;
   }

   // Add title above the list
   const titleElement = document.createElement('h5');
   titleElement.textContent = `${title} (${list.length} 条):`;
   titleElement.style.marginBottom = '5px';
   titleElement.style.marginTop = '0';
   window.danmakuOutputArea.appendChild(titleElement);

   list.forEach((item, index) => {
       const itemElement = document.createElement('div');
       itemElement.classList.add('danmaku-item-part'); // Use the styling class

       // Use the formatter function or default to plain text string
       // Ensure item is not null/undefined before passing to formatter
       const formattedContent = itemFormatter ? itemFormatter(item, index) : `(${index + 1}) ${item}`;
       itemElement.innerHTML = formattedContent;

       window.danmakuOutputArea.appendChild(itemElement);
   });

    if (typeof window.updateStatus === 'function') window.updateStatus(`${title} 加载完成，共 ${list.length} 条。`, "success");
    console.debug(`UI_Utils: Displayed ${list.length} items for "${title}".`);
}

// Handles click on the output area to copy content to clipboard.
// Assumes updateStatus is globally available via window.updateStatus.
function handleCopyOutputArea() {
    if (!window.danmakuOutputArea || !window.danmakuOutputArea.classList.contains('copyable')) {
        console.log("UI_Utils: Output area not copyable or empty.");
        return;
    }
    const textToCopy = window.danmakuOutputArea.innerText.trim(); // Use innerText to get visible text
   if (!textToCopy || textToCopy === "正在加载..." || textToCopy.startsWith("未找到")) {
        console.log("UI_Utils: Nothing to copy or content is placeholder.");
        return;
    }

   // Remove the title and numbering/labels from the copied text
   // Simple approach: split lines, remove title line, remove numbering like "(1) " and labels like "弹幕: "
   const lines = textToCopy.split('\n').filter(line => line.trim() !== ''); // Filter out empty lines
   const formattedLines = lines.map(line => {
        // Remove title line (heuristic: contains "条):" )
        if (line.includes("条):")) return null;

        // Remove numbering like "(1) " or "(1) 弹幕:"
        let cleanedLine = line.replace(/^\(\d+\)\s*/, ''); // Remove "(num) " at the start
        // Remove "弹幕: " or "提示: " if present (from Reversal)
        cleanedLine = cleanedLine.replace(/^弹幕:\s*/, '').replace(/^提示:\s*/, '');
        return cleanedLine.trim();
   }).filter(line => line !== null && line !== ''); // Filter out title line and any lines that become empty after cleaning

    const finalCopiedText = formattedLines.join('\n'); // Join cleaned lines with newlines

    if (finalCopiedText) {
        navigator.clipboard.writeText(finalCopiedText)
           .then(() => {
               console.log("UI_Utils: Text copied to clipboard:", finalCopiedText);
               if (typeof window.updateStatus === 'function') window.updateStatus("弹幕/语录已复制到剪贴板。", "success");
           })
           .catch(err => {
               console.error("UI_Utils: Failed to copy text:", err);
               if (typeof window.updateStatus === 'function') window.updateStatus("复制失败。", "error");
           });
    } else {
         console.log("UI_Utils: No valid text to copy after filtering.");
         if (typeof window.updateStatus === 'function') window.updateStatus("没有可复制的有效文本。", "warning");
    }
}

// Handles click on a search result item (delegated from results container).
// event: The click event object.
// 修改为通用的搜索结果点击处理函数
function handleSearchResultClick(event) {
    const resultItem = event.target.closest('.search-result-item');
    if (resultItem) {
        const parentDiv = resultItem.closest('.search-results');
        if (parentDiv === window.streamerSearchResultsDiv && window.streamerSearchInput) {
            window.streamerSearchInput.value = resultItem.textContent;
            window.streamerSearchResultsDiv.style.display = 'none';
        } else if (parentDiv === window.reversalSearchResultsDiv && window.streamerSearchInputReversal) {
            window.streamerSearchInputReversal.value = resultItem.textContent;
            window.reversalSearchResultsDiv.style.display = 'none';
        }
        console.log(`UI_Utils: 选择的主播/主题: ${resultItem.textContent}`);
    }
}

// 修改为通用的全局点击处理函数
function handleGlobalClick(event) {
    if (window.streamerSearchInput && window.streamerSearchResultsDiv) {
        const searchContainer = window.streamerSearchInput.closest('.search-container');
        if (searchContainer && !searchContainer.contains(event.target)) {
            window.streamerSearchResultsDiv.style.display = 'none';
            console.debug("UI_Utils: 全局点击时隐藏常规搜索结果。");
        }
    }

    if (window.streamerSearchInputReversal && window.reversalSearchResultsDiv) {
        const searchContainer = window.streamerSearchInputReversal.closest('.search-container');
        if (searchContainer && !searchContainer.contains(event.target)) {
            window.reversalSearchResultsDiv.style.display = 'none';
            console.debug("UI_Utils: 全局点击时隐藏反转搜索结果。");
        }
    }
}

// Helper for updating the simple progress text display
// Assumes progressSpan is globally available via window.progressSpan.
function updateProgress(currentIndex, totalEvents) {
    if (window.progressSpan) { // Ensure progressSpan element is correctly acquired
        if (totalEvents > 0 && currentIndex !== undefined && currentIndex >= -1) { // Index can be -1
            const displayIndex = currentIndex >= 0 ? currentIndex + 1 : 0; // Display 1-based or 0 if -1
            const percentage = totalEvents > 0 ? Math.round((displayIndex / totalEvents) * 100) : 0;
            window.progressSpan.textContent = `进度: ${displayIndex}/${totalEvents} (${percentage}%)`;
        } else {
            window.progressSpan.textContent = "进度: -"; // Default or invalid state
        }
    } else {
         console.warn("UI_Utils: progressSpan element not found. Cannot update progress.");
    }
}

// Optional Handlers for status clicks (currently just logs)
// function handleConnectionStatusCircle() { console.log("UI_Utils: Connection status circle clicked."); }
// function handleStatusMessage() { console.log("UI_Utils: Status message clicked."); }


// Expose utility functions globally via window object so they can be accessed by other files
// Accessing via window.* is slightly safer than just declaring them at top level
// and assuming load order implicitly makes them available everywhere.
window.updateLoadButtonState = updateLoadButtonState;
window.disableAutoSendButtons = disableAutoSendButtons;
window.reEnableAutoSendButtons = reEnableAutoSendButtons;
window.disableNavigationButtons = disableNavigationButtons;
window.reEnableNavigationButtons = reEnableNavigationButtons;
window.disableScriptBrowse = disableScriptBrowse;
window.reEnableScriptBrowse = reEnableScriptBrowse;
window.clearOutputArea = clearOutputArea;
window.displayFetchedList = displayFetchedList;
window.handleCopyOutputArea = handleCopyOutputArea;
window.handleSearchResultClick = handleSearchResultClick; // Used by event delegation
window.handleGlobalClick = handleGlobalClick; // Used by event delegation
window.updateProgress = updateProgress;
// window.handleConnectionStatusCircle = handleConnectionStatusCircle; // Optional expose
// window.handleStatusMessage = handleStatusMessage; // Optional expose

console.log("presenter_ui_utils.js loaded.");
