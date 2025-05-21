// static/presenter_roast_handlers.js
// Handles WebSocket messages and UI interactions related to the roast mode.
// Assumes global DOM variables (window.*) are assigned in presenter_init.js.
// Assumes sendMessage and updateStatus (window.*) are available from presenter_core.js.
// Assumes UI utility functions (window.*) are available.

// --- Handler Functions (Called by Event Listeners or presenter_init.js's dispatcher) ---

// Handles click on the "Start Roast Sequence" button.
function handleStartRoastSequence() {
    // Access global vars and check existence
    if (!window.roastTargetNameInput || !window.startRoastBtn || !window.roastStatusDiv) {
        console.warn("Roast_Handlers: Missing DOM elements for starting roast.");
        return;
    }

    const targetName = window.roastTargetNameInput.value.trim();
    if (!targetName) {
        if (typeof window.updateStatus === 'function') window.updateStatus("请输入黑粉昵称。", "warning");
        window.roastTargetNameInput.focus();
        return;
    }

     // Assumes sendMessage is globally available via window.sendMessage
    if (typeof window.sendMessage === 'function') {
         // Disable buttons while fetching/starting (server will also send auto_send_started)
         // Disabling is handled by disableAutoSendButtons helper
        if (typeof window.disableAutoSendButtons === 'function') window.disableAutoSendButtons();
        else console.warn("Roast_Handlers: disableAutoSendButtons function not available.");


        window.roastStatusDiv.textContent = `正在获取 ${targetName} 的怼人语录...`;
        if (typeof window.updateStatus === 'function') window.updateStatus("开始获取怼人语录...", "info");

        console.log("Roast_Handlers: Sending action: 'get_roast_sequence' with target:", targetName);
        window.sendMessage({ action: "get_roast_sequence", target_name: targetName }); // Correct action and data
    } else {
         console.error("Roast_Handlers: sendMessage function not available.");
         if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
    }
}

// Handles click on the "Send Danmaku and Next Prompt" button.
function handleAdvanceRoastSequence() {
    // Access global vars and check existence
    if (!window.advanceRoastBtn || !window.roastStatusDiv || !window.currentLineDiv || !window.currentPromptDiv) {
        console.warn("Roast_Handlers: Missing DOM elements for advancing roast.");
        return;
    }

    if (!window.advanceRoastBtn.disabled && window.advanceRoastBtn.style.display !== 'none') { // Check if enabled and visible
         // Assumes sendMessage is globally available via window.sendMessage
        if (typeof window.sendMessage === 'function') {
             // Disable button immediately to prevent double clicks
            window.advanceRoastBtn.disabled = true;
             if (window.exitRoastBtn) window.exitRoastBtn.disabled = true; // Disable exit temporarily

            window.roastStatusDiv.textContent = "正在发送弹幕并获取下一提示...";
            if (typeof window.updateStatus === 'function') window.updateStatus("发送怼人弹幕...", "info");

            console.log("Roast_Handlers: Sending action: 'advance_roast'.");
            window.sendMessage({ action: "advance_roast" }); // Correct action (no data needed)
        } else {
             console.error("Roast_Handlers: sendMessage function not available.");
             if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
        }
    } else {
         console.log("Roast_Handlers: advanceRoastBtn is disabled or not visible.");
    }
}

// Handles click on the "Exit Roast Mode" button.
function handleExitRoastMode() {
    // Access global vars and check existence
    if (!window.exitRoastBtn || !window.roastStatusDiv) {
         console.warn("Roast_Handlers: Missing DOM elements for exiting roast.");
         return;
    }

    if (!window.exitRoastBtn.disabled && window.exitRoastBtn.style.display !== 'none') { // Check if enabled and visible
         // Assumes sendMessage is globally available via window.sendMessage
        if (typeof window.sendMessage === 'function') {
             // Disable button immediately
            window.exitRoastBtn.disabled = true;
             if (window.startRoastBtn) window.startRoastBtn.disabled = true; // Also disable start button
             if (window.advanceRoastBtn) window.advanceRoastBtn.disabled = true; // Also disable advance button


            window.roastStatusDiv.textContent = "正在退出怼人模式...";
            if (typeof window.updateStatus === 'function') window.updateStatus("请求退出怼人模式...", "info");

            console.log("Roast_Handlers: Sending action: 'exit_roast_mode'.");
            window.sendMessage({ action: "exit_roast_mode" }); // Correct action (no data needed)
            // Server will send 'roast_sequence_finished' which handles UI cleanup
        } else {
             console.error("Roast_Handlers: sendMessage function not available.");
             if (typeof window.updateStatus === 'function') window.updateStatus("WebSocket功能未初始化。", "error");
        }
    } else {
        console.log("Roast_Handlers: exitRoastBtn is disabled or not visible.");
    }
}


// Handles message indicating roast sequence is ready.
// data: { target_name, total_roasts, message, context }
// Assumes global DOM variables are assigned.
// Assumes disableAutoSendButtons, reEnableAutoSendButtons are available via window.*
function handleRoastSequenceReadyMessage(data) {
    console.debug("Roast_Handlers: Received roast_sequence_ready:", data);
    if (window.roastStatusDiv) window.roastStatusDiv.textContent = data.message || `已为 ${data.target_name || '目标'} 加载 ${data.total_roasts} 条语录，点击 '发送弹幕并看下一提示' 开始。`;
    if (typeof window.updateStatus === 'function') window.updateStatus("怼人序列就绪。", "success");

    // Hide start button, show advance and exit buttons
    if (window.startRoastBtn) window.startRoastBtn.style.display = 'none';
    if (window.advanceRoastBtn) {
         window.advanceRoastBtn.style.display = 'inline-block';
         window.advanceRoastBtn.disabled = false; // Enable advance
    } else console.warn("Roast_Handlers: advanceRoastBtn element not found for sequence ready.");

    if (window.exitRoastBtn) {
         window.exitRoastBtn.style.display = 'inline-block';
         window.exitRoastBtn.disabled = false; // Enable exit
    } else console.warn("Roast_Handlers: exitRoastBtn element not found for sequence ready.");


    if (window.roastTargetNameInput) window.roastTargetNameInput.disabled = true; // Keep input disabled during sequence
     else console.warn("Roast_Handlers: roastTargetNameInput element not found for sequence ready.");

    // Disable script navigation/browsing and other auto-send buttons using the utility helper
    if (typeof window.disableAutoSendButtons === 'function') window.disableAutoSendButtons();
    else console.warn("Roast_Handlers: disableAutoSendButtons function not available.");

    console.debug("Roast_Handlers: UI updated for sequence ready.");
}

// Handles message updating the presenter's prompt during the roast sequence.
// data: { presenter_line, raw_template, current_roast_num, total_roasts, target_name, context }
// Assumes global DOM variables are assigned.
function handlePresenterRoastUpdateMessage(data) {
    console.debug("Roast_Handlers: Received presenter_roast_update:", data);
     // Update UI for the current roast step
    if (window.currentLineDiv) window.currentLineDiv.textContent = data.presenter_line || ""; // Access global var
    if (window.currentPromptDiv) window.currentPromptDiv.textContent = `[${data.current_roast_num}/${data.total_roasts}] 原文: ${data.raw_template || ''}`; // Access global var
    if (window.roastStatusDiv) window.roastStatusDiv.textContent = `正在进行怼人序列 (${data.current_roast_num}/${data.total_roasts}) for ${data.target_name || ''}. 点击 '发送弹幕并看下一提示' 继续.`;
    if (typeof window.updateStatus === 'function') window.updateStatus("怼人步骤更新。", "info");

    // Re-enable advance and exit buttons for the next step
    if (window.advanceRoastBtn) window.advanceRoastBtn.disabled = false;
    if (window.exitRoastBtn) window.exitRoastBtn.disabled = false;
    console.debug("Roast_Handlers: UI updated for roast step.");
}

// Handles message indicating the roast sequence has finished.
// data: { message, target_name, context }
// Assumes global DOM variables are assigned.
// Assumes reEnableAutoSendButtons is available via window.*
function handleRoastSequenceFinishedMessage(data) {
    console.debug("Roast_Handlers: Received roast_sequence_finished:", data);
    if (window.roastStatusDiv) window.roastStatusDiv.textContent = data.message || "怼人环节已结束。";
    if (typeof window.updateStatus === 'function') window.updateStatus("怼人序列结束。", "info");

    // Hide advance/exit buttons, show start button
    if (window.advanceRoastBtn) window.advanceRoastBtn.style.display = 'none';
    if (window.exitRoastBtn) window.exitRoastBtn.style.display = 'none';
    if (window.startRoastBtn) {
         window.startRoastBtn.style.display = 'inline-block';
         // Re-enabling start button and input is handled by reEnableAutoSendButtons helper
    } else console.warn("Roast_Handlers: startRoastBtn element not found for sequence finished.");


    // The 're_enable_auto_send_buttons' message from server will trigger the reEnableAutoSendButtons helper,
    // which re-enables the start button and input, and script navigation/browsing.
    console.debug("Roast_Handlers: UI updated for sequence finished.");
}


// Expose handlers globally via window object so they can be called by event listeners or dispatcher
window.handleStartRoastSequence = handleStartRoastSequence; // Called by event listener in init.js
window.handleAdvanceRoastSequence = handleAdvanceRoastSequence; // Called by event listener in init.js and keyboard handler
window.handleExitRoastMode = handleExitRoastMode; // Called by event listener in init.js
window.handleRoastSequenceReadyMessage = handleRoastSequenceReadyMessage; // Called by init.js dispatcher
window.handlePresenterRoastUpdateMessage = handlePresenterRoastUpdateMessage; // Called by init.js dispatcher
window.handleRoastSequenceFinishedMessage = handleRoastSequenceFinishedMessage; // Called by init.js dispatcher

console.log("presenter_roast_handlers.js loaded.");
