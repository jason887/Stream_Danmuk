// static/presenter_script_handlers.js
// Handles WebSocket messages and UI interactions related to script browsing and navigation.
// Assumes global DOM variables (window.*) are assigned in presenter_init.js.
// Assumes sendMessage and updateStatus (window.*) are available from presenter_core.js.
// Assumes UI utility functions (window.*) like updateLoadButtonState, updateProgress are available.

// --- Handler Functions (Called by Event Listeners or presenter_init.js's dispatcher) ---

// Handles message updating script options (directories and files).
// data: { current_path, breadcrumb: [{name, path}], options: [{name, path, type: 'browse_dir' | 'script_file'}] }
function handleScriptOptionsMessage(data) {
    console.debug("Script_Handlers: Received script_options_update:", data);
    const options = data.options; // List of {name, path, type}
    const currentPath = data.current_path; // Relative path string
    const breadcrumb = data.breadcrumb; // List of {name, path}

    if (window.scriptSelect) { // Access global var
        window.scriptSelect.innerHTML = ''; // Clear existing options
        if (options && options.length > 0) {
            options.forEach(item => {
                const option = document.createElement('option');
                option.value = item.path; // Use relative path as value
                option.textContent = item.name; // Display name (includes / for dirs)
                option.dataset.is_dir = item.type === 'browse_dir'; // Store directory status
                window.scriptSelect.appendChild(option);
            });
             // Update load button state based on new options using the utility function
             if (typeof window.updateLoadButtonState === 'function') window.updateLoadButtonState();
             else console.warn("Script_Handlers: updateLoadButtonState function not available.");

             window.scriptSelect.disabled = false; // Ensure select is enabled (unless disabled by modal state handled elsewhere)
        } else {
            const option = document.createElement('option');
            option.value = "";
            option.textContent = "-- 无可用脚本或目录 --";
            window.scriptSelect.appendChild(option);
             if (window.loadSelectedScriptBtn) window.loadSelectedScriptBtn.disabled = true;
             window.scriptSelect.disabled = true;
        }
        console.debug("Script_Handlers: Script options updated in select.");
    } else {
         console.warn("Script_Handlers: scriptSelect element not found for script_options_update.");
    }

    // Update breadcrumb display
    if (window.scriptPathBreadcrumb) { // Access global var
         // Build breadcrumb HTML with links
        window.scriptPathBreadcrumb.innerHTML = breadcrumb.map((item, index) => {
            if (index === breadcrumb.length - 1) {
                // Last item is current directory, not a link
                return item.name;
            } else {
                // Other items are links to navigate. Use data-path to store path.
                // Call a globally exposed handler function on click
                return `<a href="#" data-path="${item.path}" onclick="window.handleBreadcrumbClick(event);">${item.name}</a>`;
            }
        }).join(' > ');
         console.debug("Script_Handlers: Breadcrumb display updated.");
    } else {
         console.warn("Script_Handlers: scriptPathBreadcrumb element not found for script_options_update.");
    }


    // Show/hide browse up button (based on currentPath not being root ".")
    if (window.scriptBrowseUpBtn) { // Access global var
        if (currentPath && currentPath !== '.' && currentPath !== '') {
            window.scriptBrowseUpBtn.style.display = 'inline-block';
        } else {
            window.scriptBrowseUpBtn.style.display = 'none';
        }
        // browse up button disabled state is managed by reEnableScriptBrowse
        console.debug("Script_Handlers: Browse up button visibility updated.");
    } else {
         console.warn("Script_Handlers: scriptBrowseUpBtn element not found for script_options_update.");
    }

     if (typeof window.updateStatus === 'function') window.updateStatus("脚本列表更新。", "info");
}

// Handles double click on an item in the script select list.
function handleScriptSelectDblClick() {
    if (!window.scriptSelect) return; // Access global var
    const selectedOption = window.scriptSelect.options[window.scriptSelect.selectedIndex];
    if (!selectedOption) return;

    const selectedPath = selectedOption.value;
    const isDir = selectedOption.dataset.is_dir === 'true'; // Check data attribute

     // Assumes sendMessage is globally available via window.sendMessage
    if (typeof window.sendMessage === 'function') {
        if (isDir) {
            console.log("Script_Handlers: Double clicked directory, sending 'browse_scripts' action:", selectedPath);
            window.sendMessage({ action: "browse_scripts", path: selectedPath });
            if (typeof window.updateStatus === 'function') window.updateStatus(`浏览目录 "${selectedPath}"...`, "info");
        } else {
            console.log("Script_Handlers: Double clicked file, sending 'load_script' action:", selectedPath);
            window.sendMessage({ action: "load_script", filename: selectedPath });
            if (typeof window.updateStatus === 'function') window.updateStatus(`加载脚本 "${selectedPath}"...`, "info");
        }
    } else {
         console.error("Script_Handlers: sendMessage function not available.");
         if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}

 // Handles click on the "Load Selected Script" button.
function handleLoadSelectedScript() {
    if (!window.loadSelectedScriptBtn || !window.scriptSelect) return; // Access global vars

    if (!window.loadSelectedScriptBtn.disabled) { // Check if UI element is enabled
        const selectedOption = window.scriptSelect.options[window.scriptSelect.selectedIndex];
         if (!selectedOption || selectedOption.value === "") return; // Should be disabled if no selection, but double check

        const selectedPath = selectedOption.value;
        const isDir = selectedOption.dataset.is_dir === 'true';

        if (!isDir) { // Only load if it's a file
             // Assumes sendMessage is globally available via window.sendMessage
            if (typeof window.sendMessage === 'function') {
                 console.log("Script_Handlers: loadSelectedScriptBtn clicked, sending 'load_script' action:", selectedPath);
                 window.sendMessage({ action: "load_script", filename: selectedPath });
                 if (typeof window.updateStatus === 'function') window.updateStatus(`正在加载脚本 "${selectedPath}"...`, "info");
            } else {
                 console.error("Script_Handlers: sendMessage function not available.");
                 if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
            }
        } else {
             console.log("Script_Handlers: Cannot load a directory via load button.");
             if (typeof window.updateStatus === 'function') window.updateStatus("请选择一个脚本文件加载，双击文件夹进入。", "warning");
        }
    } else {
         console.log("Script_Handlers: loadSelectedScriptBtn is disabled.");
         // Status message might already be set indicating why it's disabled (e.g. no selection, roast mode)
    }
}

 // Handles click on the "Browse Up" button.
function handleBrowseUp() {
    if (!window.scriptBrowseUpBtn) return; // Access global var

    if (!window.scriptBrowseUpBtn.disabled) { // Check if UI element is enabled
         // Assumes sendMessage is globally available via window.sendMessage
        if (typeof window.sendMessage === 'function') {
            console.log("Script_Handlers: scriptBrowseUpBtn clicked, sending 'browse_scripts' action with '..'");
            window.sendMessage({ action: "browse_scripts", path: ".." }); // Send ".." to go up one level
            if (typeof window.updateStatus === 'function') window.updateStatus("返回上一级目录...", "info");
        } else {
             console.error("Script_Handlers: sendMessage function not available.");
             if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
        }
    } else {
         console.log("Script_Handlers: scriptBrowseUpBtn is disabled.");
    }
}

 // Handles click on a breadcrumb link (called by inline onclick in HTML).
 // event: The click event object.
function handleBreadcrumbClick(event) {
     event.preventDefault(); // Prevent default link behavior
     const path = event.target.dataset.path; // Get path from data attribute

     if (path !== undefined) {
         // Assumes sendMessage is globally available via window.sendMessage
        if (typeof window.sendMessage === 'function') {
             console.log("Script_Handlers: Breadcrumb clicked, sending 'browse_scripts' action:", path);
             window.sendMessage({ action: "browse_scripts", path: path });
             if (typeof window.updateStatus === 'function') window.updateStatus(`浏览目录 "${path}"...`, "info");
        } else {
             console.error("Script_Handlers: sendMessage function not available.");
             if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
        }
     }
}


// Handles message updating the current script event display.
// data: { script_filename, total_events, event_index, current_line, current_prompt, is_roast_mode, roast_target, roast_templates_count }
// Assumes global DOM variables (window.*) are assigned.
// Assumes updateProgress is globally available via window.updateProgress.
function handleCurrentEventUpdateMessage(data) {
    console.debug("Script_Handlers: Received current_event_update:", data);
    // Update script info display
    if (window.scriptNameSpan) window.scriptNameSpan.textContent = data.script_filename || "未加载";
    if (window.totalEventsSpan) window.totalEventsSpan.textContent = data.total_events !== undefined && data.total_events >= 0 ? data.total_events : '-';
    if (window.currentEventIndexSpan) window.currentEventIndexSpan.textContent = data.event_index !== undefined && data.event_index > -1 ? data.event_index + 1 : "-";

    // Update progress display using the helper function
     if (typeof window.updateProgress === 'function') window.updateProgress(data.event_index, data.total_events);
     else console.warn("Script_Handlers: updateProgress function not available.");


    // Update line/prompt display based on roast mode state
    if (!data.is_roast_mode) {
        if (window.currentLineDiv) window.currentLineDiv.textContent = data.current_line || "";
        if (window.currentPromptDiv) window.currentPromptDiv.textContent = data.current_prompt || "-";
         // When exiting roast mode, roastStatusDiv is cleared by handleRoastSequenceFinishedMessage
    } else {
         // If roast mode IS active, clear script lines and show roast info placeholders
        if (window.currentLineDiv) window.currentLineDiv.textContent = "进入怼黑粉模式...";
        if (window.currentPromptDiv) window.currentPromptDiv.textContent = "请按'发送弹幕并看下一提示'按钮"; // Initial prompt for roast
         // Roast status is primarily updated by handleRoastSequenceReadyMessage and handlePresenterRoastUpdateMessage
         // Clear script info if in roast mode? Or just line/prompt? Let's keep script info visible.
    }


    // Enable/disable navigation buttons based on state and roast mode
    const scriptLoaded = data.total_events > 0;
    const atStart = data.event_index <= 0;
    const atEnd = data.event_index >= data.total_events - 1;

    // Disable if no script, at start/end, OR in roast mode
    if (window.prevEventBtn) window.prevEventBtn.disabled = !scriptLoaded || atStart || data.is_roast_mode;
    if (window.nextEventBtn) window.nextEventBtn.disabled = !scriptLoaded || atEnd || data.is_roast_mode;

    // Disable script browsing/loading buttons if roast mode is active
    // This is also handled by reEnableAutoSendButtons, but setting explicitly here on state update is robust.
    const disableBrowseControls = data.is_roast_mode;
    if (window.scriptSelect) window.scriptSelect.disabled = disableBrowseControls;
    if (window.loadSelectedScriptBtn && window.scriptSelect) { // Re-evaluate load button based on selection and roast state
         const selectedOption = window.scriptSelect.options[window.scriptSelect.selectedIndex];
         // Disabled if disableBrowseControls is true, OR if no selection/it's a directory
        window.loadSelectedScriptBtn.disabled = disableBrowseControls || !selectedOption || selectedOption.value === "" || selectedOption.dataset.is_dir === 'true';
    } else if (window.loadSelectedScriptBtn) { // Handle case where scriptSelect is missing
         window.loadSelectedScriptBtn.disabled = disableBrowseControls;
    }

    if (window.scriptBrowseUpBtn) window.scriptBrowseUpBtn.disabled = disableBrowseControls;

    console.debug("Script_Handlers: Script display and navigation state updated.");
}

// Handles click on the "Previous Event" button.
function handlePrevEvent() {
     if (!window.prevEventBtn) return; // Access global var
    if (!window.prevEventBtn.disabled) { // Check if UI element is enabled
         // Assumes sendMessage is globally available via window.sendMessage
        if (typeof window.sendMessage === 'function') {
            console.log("Script_Handlers: prevEventBtn clicked, sending 'prev_event' action...");
            window.sendMessage({ action: "prev_event" });
        } else {
             console.error("Script_Handlers: sendMessage function not available.");
             if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
        }
    } else {
        console.log("Script_Handlers: prevEventBtn is disabled.");
    }
}

// Handles click on the "Next Event" button.
function handleNextEvent() {
     if (!window.nextEventBtn) return; // Access global var
    if (!window.nextEventBtn.disabled) { // Check if UI element is enabled
         // Assumes sendMessage is globally available via window.sendMessage
        if (typeof window.sendMessage === 'function') {
            console.log("Script_Handlers: nextEventBtn clicked, sending 'next_event' action...");
            window.sendMessage({ action: "next_event" });
        } else {
             console.error("Script_Handlers: sendMessage function not available.");
             if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
        }
    } else {
         console.log("Script_Handlers: nextEventBtn is disabled.");
    }
}

// Handles keyboard shortcuts for script navigation and roast mode advance.
// event: The keyboard event object.
// Assumes global DOM variables are assigned.
// Assumes handleAdvanceRoastSequence is globally available via window.handleAdvanceRoastSequence.
function handleKeyboardShortcuts(event) {
     // Ensure elements exist before checking disabled state
     const nextBtnEnabled = window.nextEventBtn && !window.nextEventBtn.disabled; // Access global var
     const advanceBtnVisibleAndEnabled = window.advanceRoastBtn && window.advanceRoastBtn.style.display !== 'none' && !window.advanceRoastBtn.disabled; // Access global var
     const prevBtnEnabled = window.prevEventBtn && !window.prevEventBtn.disabled; // Access global var


    if (event.code === 'Space' || event.code === 'PageDown') {
         // Space or PgDn triggers Next Script Event or Advance Roast
        if (nextBtnEnabled) {
            event.preventDefault(); // Prevent default only if we handle the key
            handleNextEvent(); // Call handler defined in this file
        } else if (advanceBtnVisibleAndEnabled) {
            event.preventDefault();
            // Call handler defined in roast_handlers.js (must be globally available)
             if (typeof window.handleAdvanceRoastSequence === 'function') window.handleAdvanceRoastSequence();
             else console.warn("Script_Handlers: handleAdvanceRoastSequence function not available for keyboard shortcut.");
        }
    } else if (event.code === 'PageUp') {
        // PgUp triggers Previous Script Event
        if (prevBtnEnabled) {
            event.preventDefault();
            handlePrevEvent(); // Call handler defined in this file
        }
    }
     // Add other keyboard shortcuts if needed
}


// Expose handlers globally via window object so they can be called by event listeners or dispatcher
window.handleScriptOptionsMessage = handleScriptOptionsMessage; // Called by init.js dispatcher
window.handleScriptSelectDblClick = handleScriptSelectDblClick; // Called by event listener in init.js
window.handleLoadSelectedScript = handleLoadSelectedScript; // Called by event listener in init.js
window.handleBrowseUp = handleBrowseUp; // Called by event listener in init.js
window.handleBreadcrumbClick = handleBreadcrumbClick; // Called by inline onclick in HTML
window.handleCurrentEventUpdateMessage = handleCurrentEventUpdateMessage; // Called by init.js dispatcher
window.handlePrevEvent = handlePrevEvent; // Called by event listener in init.js and keyboard handler
window.handleNextEvent = handleNextEvent; // Called by event listener in init.js and keyboard handler
window.handleKeyboardShortcuts = handleKeyboardShortcuts; // Called by event listener in init.js


console.log("presenter_script_handlers.js loaded.");
