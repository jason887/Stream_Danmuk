// static/presenter_script_handlers.js
// Handles WebSocket messages and UI interactions related to general scripts
// and the "反转主播名 (剧本模式)" (Reversed Anchor Name - Script Mode) feature.

// Assumes global DOM variables (window.*) are declared in presenter_dom_vars.js and assigned in presenter_init.js.
// Assumes sendMessage and updateStatus (window.*) are available from presenter_core.js.
// Assumes displayFetchedList (window.*) is available from presenter_ui_utils.js.

// --- Reversed Anchor Name (Script Mode) Handlers ---

// Called when the "加载反转剧本列表" button is clicked.
function handleLoadReversalScriptsRequest() {
    if (typeof window.sendMessage === 'function') {
        if (typeof window.updateStatus === 'function') window.updateStatus("正在加载反转剧本列表...", "info");
        if (typeof window.clearOutputArea === 'function') window.clearOutputArea(); // Clear previous results
        // Clear the specific presenter display area for this feature
        if (window.presenterScriptLineDisplay) {
            window.presenterScriptLineDisplay.textContent = "选择反转剧本后，您的提示将显示在此处。";
        } else {
            console.warn("Script_Handlers: presenterScriptLineDisplay element not found to clear.");
        }

        console.log("Script_Handlers: Sending action: fetch_reversal_scripts_request");
        window.sendMessage({ action: "fetch_reversal_scripts_request" }); 
        // Server will respond with "reversal_scripts_list"
    } else {
        console.error("Script_Handlers: sendMessage function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}

// Called when the server sends the list of reversal scripts.
function handleReversalScriptsListMessage(data) {
    console.log("Script_Handlers: Received reversal_scripts_list:", data);
    const scriptsList = Array.isArray(data.scripts_list) ? data.scripts_list : []; 

    if (typeof window.displayFetchedList === 'function') {
        window.displayFetchedList(
            scriptsList, 
            `选择一个反转剧本 (共 ${scriptsList.length} 条):`, 
            (item, index) => { // itemFormatter
                // Display the full script initially, or just a part of it as a title
                // For now, display full script, it will be split on click.
                return `(${index + 1}) ${item}`; 
            },
            (scriptText, originalItem) => { // onItemClick callback
                // scriptText here is the full script string from the list.
                handleReversalScriptSelected(scriptText);
            }
        );
    } else {
        console.warn("Script_Handlers: displayFetchedList function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("UI功能(displayFetchedList)未初始化。", "error");
    }
}

// Called when a presenter clicks on a fetched reversal script from the "弹幕结果" area.
function handleReversalScriptSelected(scriptText) {
    if (!scriptText || typeof scriptText !== 'string') {
        console.warn("Script_Handlers: Invalid script text for selection.");
        if (typeof window.updateStatus === 'function') window.updateStatus("无效的剧本内容。", "warning");
        if (window.presenterScriptLineDisplay) { // Clear display on error too
            window.presenterScriptLineDisplay.textContent = "选择反转剧本后，您的提示将显示在此处。";
        }
        return;
    }

    // Calculate the midpoint
    const midpoint = Math.floor(scriptText.length / 2);
    const audiencePart = scriptText.substring(0, midpoint);
    const presenterPart = scriptText.substring(midpoint);

    // Display presenterPart in the dedicated display area
    if (window.presenterScriptLineDisplay) {
        window.presenterScriptLineDisplay.textContent = presenterPart;
        console.log("Script_Handlers: Displayed presenter part:", presenterPart);
    } else {
        console.warn("Script_Handlers: presenterScriptLineDisplay element not found.");
    }

    // Send audiencePart to the server
    if (typeof window.sendMessage === 'function') {
        if (!audiencePart.trim()) {
             if (typeof window.updateStatus === 'function') window.updateStatus("注意：弹幕部分为空，未发送。", "warning");
             console.warn("Script_Handlers: Audience part is empty, not sending.");
             return; // Do not send if audience part is empty
        }
        const messageData = {
            action: "send_reversal_audience_part",
            audience_part: audiencePart,
            full_script: scriptText // Optionally send the full script for context or logging
        };
        console.log("Script_Handlers: Sending action: send_reversal_audience_part", messageData);
        window.sendMessage(messageData);
        if (typeof window.updateStatus === 'function') window.updateStatus(`已发送反转剧本弹幕: "${audiencePart}"`, "success");
    } else {
        console.error("Script_Handlers: sendMessage function not available.");
        if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化，无法发送。", "error");
    }
}

// --- Standard Script Handling (Existing from original file if any) ---
// This is for the main script loading/navigation, distinct from reversal scripts.
// Assuming these were in the original presenter_script_handlers.js or need to be added.

// Handles selection/deselection in the script list.
function handleScriptSelectDblClick() {
    if (window.scriptSelect && window.scriptSelect.value) {
        if (window.loadSelectedScriptBtn && !window.loadSelectedScriptBtn.disabled) {
            handleLoadSelectedScript();
        }
    }
}

// Handles click on "Load Selected Script" button.
function handleLoadSelectedScript() {
    if (window.scriptSelect && window.scriptSelect.value) {
        const selectedOption = window.scriptSelect.options[window.scriptSelect.selectedIndex];
        if (selectedOption.dataset.is_dir === 'true') {
            // It's a directory, browse into it
            if (typeof window.sendMessage === 'function') {
                window.sendMessage({ action: "browse_scripts", path: selectedOption.value });
            }
        } else {
            // It's a file, load it
            if (typeof window.sendMessage === 'function') {
                window.sendMessage({ action: "load_script", script_path: selectedOption.value });
                if(typeof window.updateStatus === 'function') window.updateStatus(`正在加载脚本: ${selectedOption.text}...`, "info");
            }
        }
    } else {
        if(typeof window.updateStatus === 'function') window.updateStatus("请先选择一个脚本或目录。", "warning");
    }
}

// Handles "Up" button for script browsing.
function handleBrowseUp() {
    if (typeof window.sendMessage === 'function') {
        window.sendMessage({ action: "browse_scripts", path: ".." });
    }
}

// Handles clicks on breadcrumb path segments for script browsing.
function handleBreadcrumbClick(path) {
    if (typeof window.sendMessage === 'function') {
        window.sendMessage({ action: "browse_scripts", path: path });
    }
}


// Handles messages about script options from the server.
function handleScriptOptionsMessage(data) {
    if (!window.scriptSelect || !window.scriptPathBreadcrumb || !window.scriptBrowseUpBtn) {
        console.warn("Script_Handlers: Script browsing DOM elements not found.");
        return;
    }
    window.scriptSelect.innerHTML = ''; // Clear existing options

    // Update breadcrumb
    window.scriptPathBreadcrumb.innerHTML = ''; // Clear existing breadcrumbs
    if (data.breadcrumb && data.breadcrumb.length > 0) {
        data.breadcrumb.forEach((part, index) => {
            const segment = document.createElement('a');
            segment.href = '#';
            segment.textContent = part.name;
            // Use an IIFE or a different approach if part.path can change before click
            segment.onclick = (function(path) {
                return function() { handleBreadcrumbClick(path); return false; };
            })(part.path);
            window.scriptPathBreadcrumb.appendChild(segment);
            if (index < data.breadcrumb.length - 1) {
                window.scriptPathBreadcrumb.appendChild(document.createTextNode(' / '));
            }
        });
    } else {
        window.scriptPathBreadcrumb.textContent = "脚本根目录";
    }
     // Show/hide "Up" button
    window.scriptBrowseUpBtn.style.display = data.can_go_up ? 'inline-block' : 'none';


    if (data.options && data.options.length > 0) {
        data.options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.path; // Full path for dirs/files
            option.textContent = opt.name;
            option.dataset.is_dir = opt.is_dir.toString(); // Store as string
            if (opt.is_dir) {
                option.textContent += '/'; // Indicate directory
                option.style.color = 'blue';
            }
            window.scriptSelect.appendChild(option);
        });
    } else {
        const option = document.createElement('option');
        option.value = "";
        option.textContent = "-- 无可用脚本或目录 --";
        option.disabled = true;
        window.scriptSelect.appendChild(option);
    }
    if (typeof window.updateLoadButtonState === 'function') window.updateLoadButtonState();
}


// Handles messages about the current script event from the server.
function handleCurrentEventUpdateMessage(data) {
    // Ensure all DOM elements are available
    if (!window.currentLineDiv || !window.currentPromptDiv || !window.scriptNameSpan || 
        !window.progressSpan || !window.prevEventBtn || !window.nextEventBtn ||
        !window.currentEventIndexSpan || !window.totalEventsSpan) {
        console.warn("Script_Handlers: One or more DOM elements for event update not found.");
        return;
    }

    window.currentLineDiv.textContent = data.current_line || "-";
    window.currentPromptDiv.textContent = data.presenter_prompt || "-";
    window.scriptNameSpan.textContent = data.script_name || "未加载";
    
    // Update event index display
    window.currentEventIndexSpan.textContent = data.current_event_index !== undefined && data.current_event_index >= 0 ? data.current_event_index + 1 : '-';
    window.totalEventsSpan.textContent = data.total_events || '-';

    // Update progress text using utility function
    if (typeof window.updateProgress === 'function') {
        window.updateProgress(data.current_event_index, data.total_events);
    } else { // Fallback if updateProgress is not available
        window.progressSpan.textContent = (data.total_events && data.total_events > 0) ?
            `事件: ${data.current_event_index !== undefined ? data.current_event_index + 1 : '-'}/${data.total_events}` : "N/A";
    }
    
    // Enable/disable navigation buttons
    window.prevEventBtn.disabled = !data.can_go_prev;
    window.nextEventBtn.disabled = !data.can_go_next;

    // If script is loaded, roast mode should be disabled (handled by reEnableAutoSendButtons)
    // If no script is loaded (e.g. data.script_name is "未加载" or empty), re-evaluate roast button state.
    if (typeof window.reEnableAutoSendButtons === 'function') {
        window.reEnableAutoSendButtons(); 
    }
}

// Handles keyboard shortcuts for script navigation.
function handleKeyboardShortcuts(event) {
    // Check if focus is on an input field, if so, don't trigger shortcuts
    if (document.activeElement && (document.activeElement.tagName.toLowerCase() === 'input' || document.activeElement.tagName.toLowerCase() === 'textarea')) {
        return;
    }

    // If roast mode is active (advanceRoastBtn is visible), Space advances roast
    if (window.advanceRoastBtn && window.advanceRoastBtn.style.display !== 'none') {
        if (event.code === 'Space') {
            event.preventDefault(); // Prevent scrolling
            if (!window.advanceRoastBtn.disabled) window.advanceRoastBtn.click();
        }
        // Other keys are not handled by roast mode for now
    } else { // Standard script navigation
        if (event.code === 'Space' || event.code === 'PageDown') {
            event.preventDefault();
            if (window.nextEventBtn && !window.nextEventBtn.disabled) window.nextEventBtn.click();
        } else if (event.code === 'PageUp') {
            event.preventDefault();
            if (window.prevEventBtn && !window.prevEventBtn.disabled) window.prevEventBtn.click();
        }
    }
}

// Clears presenter-specific script browsing path (called on disconnect by ws_core)
function clear_presenter_browse_path(websocket_unused) {
    // This function is called by ws_core.py, but the state is client-side.
    // We can reset the breadcrumb and script list to initial state.
    if (window.scriptPathBreadcrumb) window.scriptPathBreadcrumb.textContent = "选择脚本来源";
    if (window.scriptSelect) {
        window.scriptSelect.innerHTML = '<option value="">-- 等待连接 --</option>';
    }
    if (window.scriptBrowseUpBtn) window.scriptBrowseUpBtn.style.display = 'none';
    console.log("Script_Handlers: Cleared presenter script browse path display.");
}


// Expose handlers that need to be called from presenter_init.js or other modules
window.handleLoadReversalScriptsRequest = handleLoadReversalScriptsRequest;
window.handleReversalScriptsListMessage = handleReversalScriptsListMessage; 
// handleReversalScriptSelected is an internal callback.

window.handleScriptSelectDblClick = handleScriptSelectDblClick;
window.handleLoadSelectedScript = handleLoadSelectedScript;
window.handleBrowseUp = handleBrowseUp;
window.handleBreadcrumbClick = handleBreadcrumbClick;
window.handleScriptOptionsMessage = handleScriptOptionsMessage;
window.handleCurrentEventUpdateMessage = handleCurrentEventUpdateMessage;
window.handleKeyboardShortcuts = handleKeyboardShortcuts;
window.clear_presenter_browse_path = clear_presenter_browse_path; // Called by ws_core.py

console.log("presenter_script_handlers.js loaded/overwritten with reversal script logic.");
