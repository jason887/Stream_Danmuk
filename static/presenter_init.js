// static/presenter_init.js
// This is the main initialization script for the presenter control page.
// It runs after the DOM is ready and other presenter_*.js files are loaded.
// It gets DOM element references, assigns them to global variables declared in presenter_dom_vars.js,
// binds event listeners, and sets the message handler for presenter_core.js.
// Assumes presenter_core.js and presenter_dom_vars.js are loaded before this.
// Assumes handler functions like handleScriptOptionsMessage, handleStartRoastSequence etc.
// are defined and globally exposed in their respective files (script_handlers.js, roast_handlers.js, danmaku_handlers.js, ui_utils.js).

// Global DOM variables are declared in presenter_dom_vars.js.
// Global utility functions (sendMessage, updateStatus, updateLoadButtonState, disableAutoSendButtons, etc.)
// are assumed to be exposed by presenter_core.js and presenter_ui_utils.js onto the window object.

document.addEventListener('DOMContentLoaded', () => {
     console.log("presenter_init.js: DOM fully loaded. Starting initialization.");
 
     // --- Assign DOM Elements ---
     // Get elements by their IDs and assign them to the global variables declared in presenter_dom_vars.js.
     // Ensure the ID string exactly matches the HTML element ID in presenter_control.html.
     // Access the global variables using `window.` prefix or rely on them being in scope (less explicit).
     // Using window. prefix explicitly when assigning fetched elements to global vars defined elsewhere.
     // SCRIPT section
     window.scriptSelect = document.getElementById('script-select');
     window.loadSelectedScriptBtn = document.getElementById('load-selected-script-btn');
     window.scriptPathBreadcrumb = document.getElementById('script-path-breadcrumb');
     window.scriptBrowseUpBtn = document.getElementById('script-browse-up-btn');
     window.scriptNameSpan = document.getElementById('scriptName');
     window.progressSpan = document.getElementById('progress');
     window.currentEventIndexSpan = document.getElementById('currentEventIndex');
     window.totalEventsSpan = document.getElementById('totalEvents');
     window.currentLineDiv = document.getElementById('currentLine');
     window.currentPromptDiv = document.getElementById('currentPrompt');
 
     // NAVIGATION section
     window.prevEventBtn = document.getElementById('prevEventBtn');
     window.nextEventBtn = document.getElementById('nextEventBtn');
 
     // ROAST section
     window.roastTargetNameInput = document.getElementById('roastTargetName');
     window.startRoastBtn = document.getElementById('startRoastBtn');
     window.advanceRoastBtn = document.getElementById('advanceRoastBtn');
     window.exitRoastBtn = document.getElementById('exitRoastBtn');
     window.roastStatusDiv = document.getElementById('roastStatus');
 
     // BOSS DANMAKU section
     window.bossNicknameInput = document.getElementById('bossNicknameInput');
     window.giftNameInput = document.getElementById('giftNameInput');
     window.sendWelcomeBossBtn = document.getElementById('sendWelcomeBossBtn');
     window.sendThanksBossBtn = document.getElementById('sendThanksBossBtn');
 
     // GENERAL DANMAKU FETCH section
     window.streamerSearchInput = document.getElementById('streamer_search_input');
     window.streamerSearchResultsDiv = document.getElementById('streamer_search_results');
     window.fetchWelcomeDanmakuBtn = document.getElementById('fetch_welcome_danmaku_btn');
     window.fetchRoastDanmakuBtn = document.getElementById('fetch_roast_danmaku_btn');
     window.fetchReversalBtn = document.getElementById('fetch_reversal_btn');
     window.fetchCaptionsBtn = document.getElementById('fetch_captions_btn');
     window.danmakuOutputArea = document.getElementById('danmaku_output_area');
     window.autoSendDanmakuBtn = document.getElementById('autoSendDanmakuBtn'); // Auto send button
 
     // "欢迎吐槽" (Welcome Complaints) Elements
     window.reversedAnchorNameInput = document.getElementById('reversedAnchorNameInput');
     window.themeEventNameInput = document.getElementById('themeEventNameInput');
     window.confirmComplaintsBtn = document.getElementById('confirmComplaintsBtn');
 
     // "怼黑粉" (Counter Black Fans) Elements
     window.counterBlackFansBtn = document.getElementById('counterBlackFansBtn');

     // "欢迎大哥" (Welcome Big Brother) Specific Elements
     window.bigBrotherNameInput = document.getElementById('bigBrotherNameInput');
     window.sendWelcomeBigBrotherBtn = document.getElementById('sendWelcomeBigBrotherBtn');

     // "感谢大哥礼物" (Thank Big Brother for Gift) Elements
     window.giftThanksBigBrotherNameInput = document.getElementById('giftThanksBigBrotherNameInput');
     window.giftThanksGiftNameInput = document.getElementById('giftThanksGiftNameInput');
     window.sendGiftThanksBtn = document.getElementById('sendGiftThanksBtn');

     // "反转主播名" (Reversed Anchor Name) Script Mode Elements
     window.loadReversalScriptsBtn = document.getElementById('loadReversalScriptsBtn');
     window.presenterScriptLineDisplay = document.getElementById('presenterScriptLineDisplay');

     // STATUS section (assuming these exist in HTML)
     // These references are primarily used by updateStatus in presenter_core.js and ui_utils.js
     window.statusMessageDiv = document.getElementById('status-message');
     window.connectionStatusCircle = document.getElementById('connectionStatusCircle');
     // Assuming you added these IDs for the bottom status
     window.connectionStatusCircleFooter = document.getElementById('connectionStatusCircleFooter');
     window.statusTextFooter = document.querySelector('.status-text-footer');
 
 
     // Log acquisition status for critical elements (保持这个日志，方便调试)
     console.log("presenter_init.js: DOM Elements acquisition status:");
     console.log("scriptSelect:", window.scriptSelect ? "Found" : "Not Found");
     console.log("loadSelectedScriptBtn:", window.loadSelectedScriptBtn ? "Found" : "Not Found");
     console.log("startRoastBtn:", window.startRoastBtn ? "Found" : "Not Found");
     console.log("fetchWelcomeDanmakuBtn:", window.fetchWelcomeDanmakuBtn ? "Found" : "Not Found");
     console.log("sendWelcomeBossBtn:", window.sendWelcomeBossBtn ? "Found" : "Not Found");
     console.log("streamerSearchInput:", window.streamerSearchInput ? "Found" : "Not Found");
     console.log("danmakuOutputArea:", window.danmakuOutputArea ? "Found" : "Not Found");
     console.log("autoSendDanmakuBtn:", window.autoSendDanmakuBtn ? "Found" : "Not Found");
     // Log Welcome Complaints elements
     console.log("reversedAnchorNameInput:", window.reversedAnchorNameInput ? "Found" : "Not Found");
     console.log("themeEventNameInput:", window.themeEventNameInput ? "Found" : "Not Found");
     console.log("confirmComplaintsBtn:", window.confirmComplaintsBtn ? "Found" : "Not Found");
     console.log("counterBlackFansBtn:", window.counterBlackFansBtn ? "Found" : "Not Found"); 
     // Log Welcome Big Brother elements
     console.log("bigBrotherNameInput:", window.bigBrotherNameInput ? "Found" : "Not Found");
     console.log("sendWelcomeBigBrotherBtn:", window.sendWelcomeBigBrotherBtn ? "Found" : "Not Found");
     // Log Thank Big Brother for Gift elements
     console.log("giftThanksBigBrotherNameInput:", window.giftThanksBigBrotherNameInput ? "Found" : "Not Found");
     console.log("giftThanksGiftNameInput:", window.giftThanksGiftNameInput ? "Found" : "Not Found");
     console.log("sendGiftThanksBtn:", window.sendGiftThanksBtn ? "Found" : "Not Found");
     // Log Reversed Anchor Name Script Mode elements
     console.log("loadReversalScriptsBtn:", window.loadReversalScriptsBtn ? "Found" : "Not Found");
     console.log("presenterScriptLineDisplay:", window.presenterScriptLineDisplay ? "Found" : "Not Found");
     console.log("advanceRoastBtn:", window.advanceRoastBtn ? "Found" : "Not Found"); // Add more checks
     console.log("exitRoastBtn:", window.exitRoastBtn ? "Found" : "Not Found"); // Add more checks
     console.log("sendThanksBossBtn:", window.sendThanksBossBtn ? "Found" : "Not Found"); // Add more checks
     console.log("fetchRoastDanmakuBtn:", window.fetchRoastDanmakuBtn ? "Found" : "Not Found"); // Add more checks
     console.log("fetchReversalBtn:", window.fetchReversalBtn ? "Found" : "Not Found"); // Add more checks
     console.log("fetchCaptionsBtn:", window.fetchCaptionsBtn ? "Found" : "Not Found"); // Add more checks
     // 继续添加其他关键元素的日志
     console.log("prevEventBtn:", window.prevEventBtn ? "Found" : "Not Found");
     console.log("nextEventBtn:", window.nextEventBtn ? "Found" : "Not Found");
     console.log("roastTargetNameInput:", window.roastTargetNameInput ? "Found" : "Not Found");
     console.log("roastStatusDiv:", window.roastStatusDiv ? "Found" : "Not Found");
     console.log("bossNicknameInput:", window.bossNicknameInput ? "Found" : "Not Found");
     console.log("giftNameInput:", window.giftNameInput ? "Found" : "Not Found");
     console.log("streamerSearchResultsDiv:", window.streamerSearchResultsDiv ? "Found" : "Not Found");
     console.log("statusMessageDiv:", window.statusMessageDiv ? "Found" : "Not Found");
     console.log("connectionStatusCircle:", window.connectionStatusCircle ? "Found" : "Not Found");
     console.log("connectionStatusCircleFooter:", window.connectionStatusCircleFooter ? "Found" : "Not Found");
     console.log("statusTextFooter:", window.statusTextFooter ? "Found" : "Not Found");
     console.log("scriptPathBreadcrumb:", window.scriptPathBreadcrumb ? "Found" : "Not Found");
     console.log("scriptBrowseUpBtn:", window.scriptBrowseUpBtn ? "Found" : "Not Found");
     console.log("scriptNameSpan:", window.scriptNameSpan ? "Found" : "Not Found");
     console.log("progressSpan:", window.progressSpan ? "Found" : "Not Found");
     console.log("currentEventIndexSpan:", window.currentEventIndexSpan ? "Found" : "Not Found");
     console.log("totalEventsSpan:", window.totalEventsSpan ? "Found" : "Not Found");
     console.log("currentLineDiv:", window.currentLineDiv ? "Found" : "Not Found");
     console.log("currentPromptDiv:", window.currentPromptDiv ? "Found" : "Not Found");
 
     // --- Initialize UI Event Listeners ---
     initializeUIEventListeners(); // Call the function to bind listeners
 
     // --- Expose message handler to core ---
     // Make this module's message handler and re-enable utility available to presenter_core.js 
     // Assuming presenter_core.js looks for window.presenterFeatures 
     window.presenterFeatures = { 
         handleServerMessage: handleServerMessage, // Expose the message handler 
         reEnableAutoSendButtons: typeof reEnableAutoSendButtons === 'function' ? reEnableAutoSendButtons : function() {
             console.warn('reEnableAutoSendButtons is not defined.');
         } // Expose the re-enable utility 
     };
 
 
     // --- Set up the main message dispatcher ---
     // Provide the handleServerMessage function to presenter_core.js.
     // Assumes presenter_core.js exposes window.presenterCore.setMessageHandler.
      if (window.presenterCore && typeof window.presenterCore.setMessageHandler === 'function') {
           window.presenterCore.setMessageHandler(handleServerMessage); // Pass our dispatcher function
           console.log("presenter_init.js: Message handler assigned to presenterCore.");
      } else {
           console.error("presenter_init.js: presenterCore.setMessageHandler function not available. Message handling will fail.");
      }
 
     // --- Initial state requests ---
     // These requests are typically sent AFTER successful WebSocket registration.
     // The "registration_success" message is received by handleServerMessage,
     // which then triggers these initial requests.
     // No need to send them here at the very end of DOMContentLoaded.
 
     // Initial state for buttons that might be disabled.
     // The 're_enable_auto_send_buttons' message from the server after registration
     // will trigger the reEnableAutoSendButtons helper, which sets the initial button states correctly.
     // No need to explicitly call reEnableAutoSendButtons here at the very end.
 
     console.log("presenter_init.js: Initialization complete.");
 });
 
 
 // --- Main WebSocket Message Dispatcher ---
 // This function receives all messages from presenter_core.js and dispatches them
 // to the appropriate handler functions defined in other feature files.
 // Assumes handler functions are globally available (exposed by their respective files).
 // Assumes updateStatus, disableAutoSendButtons, reEnableAutoSendButtons are globally available.
 function handleServerMessage(type, data) {
     console.log(`presenter_init.js: Dispatching message type: ${type}`, data); // DEBUG LOG
 
     // Update core status messages using the global updateStatus function
     // Core handles registration_success, pong, and calls updateStatus internally on connection events.
     // We use updateStatus here for messages related to feature actions (fetch/send status, errors).
     if (typeof window.updateStatus === 'function') { // Check if updateStatus is available
          switch (type) {
              case "info":
                  window.updateStatus(data.message || "信息", "info");
                  break;
              case "warning":
                  window.updateStatus(data.message || "警告", "warning");
                  break;
              case "error":
                  window.updateStatus(data.message || "错误", "error");
                  // If it's an error related to an auto-send/modal task, re-enable buttons.
                  // The server also sends re_enable_auto_send_buttons on error, but this is a fallback.
                  // if (data.context && (data.context.includes("auto_send") || data.context.includes("send_boss") || data.context.includes("roast"))) {
                  //      if (typeof window.reEnableAutoSendButtons === 'function') window.reEnableAutoSendButtons();
                  // }
                  break;
              // registration_success and pong are handled by core's handleCoreMessage
              // re_enable_auto_send_buttons is handled below
          }
     } else {
          console.error("presenter_init.js: updateStatus function not available for status messages.");
     }
 
 
     // Dispatch to specific handlers defined in other files (accessed via window)
     // Ensure handlers are defined globally in their respective files.
     switch (type) {
         // Core messages handled by core's handleCoreMessage or handled above (like registration_success)
         case "registration_success":
              // This message indicates connection is ready. Trigger initial requests.
              console.log("presenter_init.js: Handling registration_success - sending initial requests.");
              if (typeof window.sendMessage === 'function') {
                   window.sendMessage({ action: "browse_scripts", path: "." }); // Request initial script list
                   window.sendMessage({ action: "get_current_state" }); // Request current script state
                   // Server also sends re_enable_auto_send_buttons after successful registration
              } else {
                  console.error("presenter_init.js: sendMessage function not available for initial requests.");
              }
              break;
         case "pong": // Handled by core
              break;
 
 
         // Script Browsing & Loading
         case "script_options_update":
             if (typeof window.handleScriptOptionsMessage === 'function') window.handleScriptOptionsMessage(data);
             else console.warn(`presenter_init.js: Handler for ${type} not found (window.handleScriptOptionsMessage).`);
             break;
 
         // Script Navigation & Display
         case "current_event_update":
             if (typeof window.handleCurrentEventUpdateMessage === 'function') window.handleCurrentEventUpdateMessage(data);
              else console.warn(`presenter_init.js: Handler for ${type} not found (window.handleCurrentEventUpdateMessage).`);
             break;
          case "end_of_script": // Server sends when next_event reaches end
              // Status update handled above
              // Navigation buttons state handled by current_event_update which follows.
              break;
 
 
         // Roast Mode
         case "roast_sequence_ready":
             if (typeof window.handleRoastSequenceReadyMessage === 'function') window.handleRoastSequenceReadyMessage(data);
              else console.warn(`presenter_init.js: Handler for ${type} not found (window.handleRoastSequenceReadyMessage).`);
             break;
         case "presenter_roast_update":
             if (typeof window.handlePresenterRoastUpdateMessage === 'function') window.handlePresenterRoastUpdateMessage(data);
              else console.warn(`presenter_init.js: Handler for ${type} not found (window.handlePresenterRoastUpdateMessage).`);
             break;
         case "roast_sequence_finished":
             if (typeof window.handleRoastSequenceFinishedMessage === 'function') window.handleRoastSequenceFinishedMessage(data);
              else console.warn(`presenter_init.js: Handler for ${type} not found (window.handleRoastSequenceFinishedMessage).`);
             // Buttons re-enabled by 're_enable_auto_send_buttons' message
             break;
 
         // Danmaku Fetch/Display
         case "danmaku_list": // Fetched Welcome/Mock list
             if (typeof window.handleDanmakuListMessage === 'function') window.handleDanmakuListMessage(data);
              else console.warn(`presenter_init.js: Handler for ${type} not found (window.handleDanmakuListMessage).`);
             break;
         case "reversal_list": // Fetched Reversal list
             if (typeof window.handleReversalListMessage === 'function') window.handleReversalListMessage(data);
              else console.warn(`presenter_init.js: Handler for ${type} not found (window.handleReversalListMessage).`);
             break;
         case "captions_list": // Fetched Social Topics list
             if (typeof window.handleCaptionsListMessage === 'function') window.handleCaptionsListMessage(data);
              else console.warn(`presenter_init.js: Handler for ${type} not found (window.handleCaptionsListMessage).`);
             break;
         case "anti_fan_quotes_list": // Fetched Anti-Fan list (optional fetch action exists on server)
             if (typeof window.handleAntiFanQuotesListMessage === 'function') window.handleAntiFanQuotesListMessage(data);
              else console.warn(`presenter_init.js: Handler for ${type} not found (window.handleAntiFanQuotesListMessage).`);
             break;
 
         // Auto-Send Status (Generic messages from server for Boss, Auto-fetched)
         case "auto_send_started":
              // Status updated above
              // Button disabling should be handled by a utility called here
              if (typeof window.disableAutoSendButtons === 'function') window.disableAutoSendButtons();
              else console.warn(`presenter_init.js: disableAutoSendButtons function not available for ${type}.`);
              break;
         case "auto_send_finished": // Status updated above
              // Re-enable is handled by 're_enable_auto_send_buttons' message
              break;
         case "auto_send_cancelled": // Status updated above
              // Re-enable is handled by 're_enable_auto_send_buttons' message
              break;
         case "re_enable_auto_send_buttons": // Signal from server/core to re-enable buttons
              console.log("presenter_init.js: Handling re_enable_auto_send_buttons.");
              if (typeof window.reEnableAutoSendButtons === 'function') window.reEnableAutoSendButtons();
              else console.warn(`presenter_init.js: reEnableAutoSendButtons function not available for ${type}.`);
              break;
 
 
         default:
             // Message type not explicitly handled by feature handlers.
             // If it's not handled by core either, a warning is logged in core.js.
             // No additional action needed here.
             // console.warn(`presenter_init.js: Received unhandled message type (dispatched): ${type}`, data); // DEBUG - Can be noisy if many unhandled
     }
 }
 
 // --- Initialize UI Event Listeners ---
 // This function is called by the DOMContentLoaded callback.
 // It binds all necessary event listeners using the globally assigned DOM variables.
 // Assumes handler functions are globally available (exposed by their respective files).
 function initializeUIEventListeners() {
     console.log("presenter_init.js: Binding UI event listeners.");
 
     // Script Browsing & Loading
     // Assumes scriptSelect, loadSelectedScriptBtn, scriptPathBreadcrumb, scriptBrowseUpBtn are global
     // Assumes handleScriptSelectDblClick, handleLoadSelectedScript, handleBrowseUp, handleBreadcrumbClick, updateLoadButtonState are global handlers/utilities.
     if (window.scriptSelect) {
          window.scriptSelect.addEventListener('dblclick', window.handleScriptSelectDblClick);
          window.scriptSelect.addEventListener('change', window.updateLoadButtonState); // Call utility function
          console.log("presenter_init.js: scriptSelect listeners added.");
     } else { console.warn("presenter_init.js: scriptSelect element not found, listeners not added."); }
 
     if (window.loadSelectedScriptBtn) {
          window.loadSelectedScriptBtn.addEventListener('click', window.handleLoadSelectedScript);
          console.log("presenter_init.js: loadSelectedScriptBtn click listener added.");
     } else { console.warn("presenter_init.js: loadSelectedScriptBtn element not found, listener not added."); }
 
     if (window.scriptBrowseUpBtn) {
          window.scriptBrowseUpBtn.addEventListener('click', window.handleBrowseUp);
          console.log("presenter_init.js: scriptBrowseUpBtn click listener added.");
     } else { console.warn("presenter_init.js: scriptBrowseUpBtn element not found, listener not added."); }
 
     // Breadcrumb links are handled by inline onclick calling window.handleBreadcrumbClick
 
 
     // Script Navigation
     // Assumes prevEventBtn, nextEventBtn are global
     // Assumes handlePrevEvent, handleNextEvent are global handlers.
     if (window.prevEventBtn) {
          window.prevEventBtn.addEventListener('click', window.handlePrevEvent);
          console.log("presenter_init.js: prevEventBtn click listener added.");
     } else { console.warn("presenter_init.js: prevEventBtn element not found, listener not added."); }
 
     if (window.nextEventBtn) {
          window.nextEventBtn.addEventListener('click', window.handleNextEvent);
          console.log("presenter_init.js: nextEventBtn click listener added.");
     } else { console.warn("presenter_init.js: nextEventBtn element not found, listener not added."); }
 
     // Add keyboard shortcuts (Space/PgDn for next/advance, PgUp for prev)
     // Assumes handleKeyboardShortcuts is a global handler.
     document.addEventListener('keydown', window.handleKeyboardShortcuts);
     console.log("presenter_init.js: Keyboard shortcuts listener added.");
 
 
     // Roast Mode
     // Assumes roastTargetNameInput, startRoastBtn, advanceRoastBtn, exitRoastBtn are global
     // Assumes handleStartRoastSequence, handleAdvanceRoastSequence, handleExitRoastMode are global handlers.
     if (window.startRoastBtn) {
          window.startRoastBtn.addEventListener('click', window.handleStartRoastSequence);
          console.log("presenter_init.js: startRoastBtn click listener added.");
     } else { console.warn("presenter_init.js: startRoastBtn element not found, listener not added."); }
 
     if (window.advanceRoastBtn) {
          window.advanceRoastBtn.addEventListener('click', window.handleAdvanceRoastSequence);
          console.log("presenter_init.js: advanceRoastBtn click listener added.");
     } else { console.warn("presenter_init.js: advanceRoastBtn element not found, listener not added."); }
 
     if (window.exitRoastBtn) {
          window.exitRoastBtn.addEventListener('click', window.handleExitRoastMode);
          console.log("presenter_init.js: exitRoastBtn click listener added.");
     } else { console.warn("presenter_init.js: exitRoastBtn element not found, listener not added."); }
 
 
     // Boss Danmaku
     // Assumes bossNicknameInput, giftNameInput, sendWelcomeBossBtn, sendThanksBossBtn are global
     // Assumes handleSendBossDanmaku is a global handler.
     if (window.sendWelcomeBossBtn) {
          window.sendWelcomeBossBtn.addEventListener('click', () => window.handleSendBossDanmaku('welcome_boss'));
          console.log("presenter_init.js: sendWelcomeBossBtn click listener added.");
     } else { console.warn("presenter_init.js: sendWelcomeBossBtn element not found, listener not added."); }
 
     if (window.sendThanksBossBtn) {
          window.sendThanksBossBtn.addEventListener('click', () => window.handleSendBossDanmaku('thanks_boss_gift'));
          console.log("presenter_init.js: sendThanksBossBtn click listener added.");
     } else { console.warn("presenter_init.js: sendThanksBossBtn element not found, listener not added."); }
 
 
     // General Danmaku Fetch
     // Assumes streamerSearchInput, streamerSearchResultsDiv, fetch buttons are global.
     // Assumes handleStreamerSearchInput, handleGlobalClick, handleSearchResultClick, handleFetchDanmakuList, handleFetchReversal, handleFetchCaptions are global handlers/utilities.
     if (window.streamerSearchInput) {
         window.streamerSearchInput.addEventListener('input', window.handleStreamerSearchInput); // For fuzzy search API call
          console.log("presenter_init.js: streamerSearchInput input listener added.");
          // Add a global click listener to hide search results when clicking outside
         document.addEventListener('click', window.handleGlobalClick); // Utility function
          console.log("presenter_init.js: Global click listener for search results added.");
     } else { console.warn("presenter_init.js: streamerSearchInput element not found, listener not added."); }
 
     // Click listener for search results (using event delegation on the container)
     if(window.streamerSearchResultsDiv) {
          window.streamerSearchResultsDiv.addEventListener('click', window.handleSearchResultClick); // Utility function
          console.log("presenter_init.js: streamerSearchResultsDiv click delegation listener added.");
     } else { console.warn("presenter_init.js: streamerSearchResultsDiv element not found, listener not added."); }
 
 
     if (window.fetchWelcomeDanmakuBtn) {
          window.fetchWelcomeDanmakuBtn.addEventListener('click', () => window.handleFetchDanmakuList('welcome')); // Handler defined in danmaku_handlers
          console.log("presenter_init.js: fetchWelcomeDanmakuBtn click listener added.");
     } else { console.warn("presenter_init.js: fetchWelcomeDanmakuBtn element not found, listener not added."); }
 
     if (window.fetchRoastDanmakuBtn) {
          window.fetchRoastDanmakuBtn.addEventListener('click', () => window.handleFetchDanmakuList('roast')); // Handler defined in danmaku_handlers
          console.log("presenter_init.js: fetchRoastDanmakuBtn click listener added.");
     } else { console.warn("presenter_init.js: fetchRoastDanmakuBtn element not found, listener not added."); }
 
     if (window.fetchReversalBtn) {
          window.fetchReversalBtn.addEventListener('click', window.handleFetchReversal); // Handler defined in danmaku_handlers
          console.log("presenter_init.js: fetchReversalBtn click listener added.");
     } else { console.warn("presenter_init.js: fetchReversalBtn element not found, listener not added."); }
 
     if (window.fetchCaptionsBtn) {
          window.fetchCaptionsBtn.addEventListener('click', window.handleFetchCaptions); // Handler defined in danmaku_handlers
          console.log("presenter_init.js: fetchCaptionsBtn click listener added.");
     } else { console.warn("presenter_init.js: fetchCaptionsBtn element not found, listener not added."); }
 
 
     // Auto Send Fetched Danmaku
     // Assumes autoSendDanmakuBtn is global and handleAutoSendFetchedDanmaku is global handler.
     if (window.autoSendDanmakuBtn) {
          window.autoSendDanmakuBtn.addEventListener('click', window.handleAutoSendFetchedDanmaku);
          console.log("presenter_init.js: autoSendDanmakuBtn click listener added.");
     } else { console.warn("presenter_init.js: autoSendDanmakuBtn element not found, listener not added."); }
 
 
     // Danmaku Output Area Click to Copy
     // Assumes danmakuOutputArea is global and handleCopyOutputArea is global utility.
     if (window.danmakuOutputArea) {
          window.danmakuOutputArea.addEventListener('click', window.handleCopyOutputArea);
          console.log("presenter_init.js: danmakuOutputArea click listener added.");
     } else { console.warn("presenter_init.js: danmakuOutputArea element not found, listener not added."); }
 
    // "欢迎吐槽" (Welcome Complaints) Button
    // Assumes confirmComplaintsBtn is global and handleFetchComplaintsDanmaku is global handler.
    if (window.confirmComplaintsBtn) {
        window.confirmComplaintsBtn.addEventListener('click', window.handleFetchComplaintsDanmaku);
        console.log("presenter_init.js: confirmComplaintsBtn click listener added.");
    } else { console.warn("presenter_init.js: confirmComplaintsBtn element not found, listener not added."); }

    // "怼黑粉" (Counter Black Fans) Button
    if (window.counterBlackFansBtn) {
        window.counterBlackFansBtn.addEventListener('click', window.handleFetchAntiFanQuotesRequest); 
        console.log("presenter_init.js: counterBlackFansBtn click listener added.");
    } else { console.warn("presenter_init.js: counterBlackFansBtn element not found, listener not added."); }

    // "欢迎大哥" (Welcome Big Brother) Button
    if (window.sendWelcomeBigBrotherBtn) {
        window.sendWelcomeBigBrotherBtn.addEventListener('click', window.handleSendWelcomeBigBrotherRequest); 
        console.log("presenter_init.js: sendWelcomeBigBrotherBtn click listener added.");
    } else { console.warn("presenter_init.js: sendWelcomeBigBrotherBtn element not found, listener not added."); }

    // "感谢大哥礼物" (Thank Big Brother for Gift) Button
    if (window.sendGiftThanksBtn) {
        window.sendGiftThanksBtn.addEventListener('click', window.handleSendGiftThanksRequest); 
        console.log("presenter_init.js: sendGiftThanksBtn click listener added.");
    } else { console.warn("presenter_init.js: sendGiftThanksBtn element not found, listener not added."); }

    // "反转主播名" (Reversed Anchor Name) Script Mode Button
    if (window.loadReversalScriptsBtn) {
        window.loadReversalScriptsBtn.addEventListener('click', window.handleLoadReversalScriptsRequest); // New handler to be created in presenter_script_handlers.js
        console.log("presenter_init.js: loadReversalScriptsBtn click listener added.");
    } else { console.warn("presenter_init.js: loadReversalScriptsBtn element not found, listener not added."); }

     // Optional Status click handlers
     // if (window.connectionStatusCircle) { window.connectionStatusCircle.addEventListener('click', window.handleConnectionStatusCircle); console.log("presenter_init.js: connectionStatusCircle click listener added."); }
     // if (window.statusMessageDiv) { window.statusMessageDiv.addEventListener('click', window.handleStatusMessage); console.log("presenter_init.js: statusMessageDiv click listener added."); }
 
 }
 
 
 console.log("presenter_init.js loaded and finished execution.");
 