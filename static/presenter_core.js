// static/presenter_core.js
// This file handles the core WebSocket connection and message dispatch

// --- Server Ports ---
const WEBSOCKET_PORT = 8765;

// --- Global Variables ---
let websocket = null; // WebSocket instance
let reconnectTimer = null;
const reconnectDelay = 3000; // 3 seconds

// Variable to hold the message handler function provided by another module (presenter_init.js)
// This handler is where messages received by core will be dispatched to.
let externalMessageHandler = null; // Renamed for clarity to avoid conflict with a local var if any


// --- DOM Elements (Core - Only what's needed here) ---
// References to status elements that *this* core file updates directly.
// Other DOM elements are handled by feature files.
let statusMessageDiv; // Will be assigned in DOMContentLoaded
let connectionStatusCircle; // Will be assigned in DOMContentLoaded
let connectionStatusCircleFooter; // Will be assigned in DOMContentLoaded
let statusTextFooter; // Will be assigned in DOMContentLoaded


// --- Helper to send WebSocket messages ---
// This function is called by feature handlers via window.sendMessage.
// It handles the actual sending and connection checks.
function sendMessage(message) {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(JSON.stringify(message));
         // console.log("Presenter_core: Sent via WebSocket:", message); // DEBUG - Can be noisy
    } else {
        console.warn("Presenter_core: WebSocket is not open. Cannot send message:", message); // DEBUG
        // Use core's updateStatus if available, otherwise basic console log
        if (typeof updateStatus === 'function') {
             updateStatus("WebSocket未连接，无法发送消息。", "status");
        } else {
             console.error("Presenter_core: updateStatus function not available.");
        }
    }
}

// --- Helper to update status message ---
// This function is called by core and potentially by feature handlers via window.updateStatus.
// It updates the main status text area and the bottom connection indicator.
function updateStatus(message, type) {
     // Update main status message text and style
     if (statusMessageDiv) { // Check if element reference is valid
          statusMessageDiv.textContent = message;
          // Use template literal for class names
          statusMessageDiv.className = `status status-text ${type}`; // e.g., 'status status-text success'
     }

     // Update bottom connection indicator as well
     if (connectionStatusCircleFooter && statusTextFooter) { // Check element references
         // Update circle color based on general type or specific messages
         if (type === 'success' || (type === 'info' && message && message.includes('已连接'))) { // Consider 'info' messages about connection as success
             connectionStatusCircleFooter.classList.remove('disconnected', 'error', 'warning');
             connectionStatusCircleFooter.classList.add('connected');
             connectionStatusCircleFooter.style.backgroundColor = '#4CAF50'; // Green
             statusTextFooter.textContent = '已连接';
             statusTextFooter.style.color = '#4CAF50'; // Green text
         } else if (type === 'error' || (type === 'info' && message && message.includes('断开')) || (type === 'status' && message && message.includes('未连接'))) { // Disconnected/Error state
             connectionStatusCircleFooter.classList.remove('connected', 'warning');
             connectionStatusCircleFooter.classList.add('disconnected', 'error');
             connectionStatusCircleFooter.style.backgroundColor = '#F44336'; // Red
             statusTextFooter.textContent = '已断开';
             statusTextFooter.style.color = '#F44336'; // Red text
         } else if (type === 'warning') {
             connectionStatusCircleFooter.classList.remove('connected', 'error');
             connectionStatusCircleFooter.classList.add('warning');
             connectionStatusCircleFooter.style.backgroundColor = '#FF9800'; // Orange/Amber
             statusTextFooter.textContent = '警告'; // Or keep previous? Let's keep simple 'Connected'/'Disconnected'
             statusTextFooter.style.color = '#FF9800';
         } else { // Default or info type not related to connection
             // Don't change circle color for other status types like info or default
             // Ensure it's not stuck in a non-connected state if connection is actually fine.
             // It's better to rely on onopen/onclose for circle state.
             // Let's simplify: only onopen/onclose change the circle visual state.
         }
     }
     // Console log is handled by the handleServerMessage dispatcher or where updateStatus is called.
}


// --- WebSocket Connection Management ---
// This function is called by this file's DOMContentLoaded handler or by the reconnect timer.
function connectWebSocket() {
    console.log("Presenter_core: Attempting to connect to WebSocket."); // DEBUG

    // Prevent multiple connection attempts if already connecting or open
    if (websocket && (websocket.readyState === WebSocket.OPEN || websocket.readyState === WebSocket.CONNECTING)) {
        console.log("Presenter_core: WebSocket is already connecting or open. Aborting connect attempt."); // DEBUG
        return;
    }

    // Clear any pending reconnect timer before starting a new attempt
    if(reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
    }

    const wsHost = window.location.hostname || 'localhost';
    const wsUrl = `ws://${wsHost}:${WEBSOCKET_PORT}/presenter`;
    console.log(`Presenter_core: Connecting to ${wsUrl}`); // DEBUG

    // Create a new WebSocket instance and assign it to the global variable
    websocket = new WebSocket(wsUrl);

    // Define event handlers
    websocket.onopen = () => {
        console.log("Presenter_core: WebSocket onopen event. State:", websocket.readyState); // DEBUG
        // Update main status and bottom indicator
        updateStatus("已连接到服务器，正在注册...", "success");

        // Send initial registration message to the server
        // sendMessage is defined in this file at the top level
        sendMessage({ action: "register", client_type: "presenter" }); // <--- Call sendMessage here
    };

    websocket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            // console.log("Presenter_core: Received raw message:", event.data); // Very verbose
            // console.log("Presenter_core: Received parsed data:", data); // DEBUG - Can be noisy


            const messageType = typeof data.type === 'string' ? data.type.trim() : data.type;

            // --- Dispatch message ---
            // First, try to handle core messages internally (like pong).
            // If not fully handled internally, dispatch to the external handler provided by presenter_init.js.

             // Handle messages that *only* core cares about internally
             if (handleCoreMessage(messageType, data)) {
                  // Message fully handled by core, do nothing further.
                  // console.debug(`Presenter_core: Fully handled core message: ${messageType}`); // Too noisy
             } else if (externalMessageHandler) {
                 // An external message handler (from presenter_init.js) is set, dispatch to it.
                  externalMessageHandler(messageType, data);
             } else {
                 // No core-only handling and no external handler is set.
                 console.warn(`Presenter_core: Received unhandled message type: ${messageType} (No external handler set)`, data); // DEBUG
                 // If updateStatus is available, provide a generic error status message.
                 if (typeof updateStatus === 'function' && messageType !== 'pong') { // Avoid status for pong
                     updateStatus(`收到未处理的消息类型: ${messageType}`, "warning");
                 }
             }


        } catch (e) {
            console.error("Presenter_core: Error parsing or processing WebSocket message:", e, event.data); // DEBUG
             // Use core's updateStatus
             updateStatus(`WebSocket消息处理错误: ${e.message}`, "error");
        }
    };

    websocket.onclose = (event) => {
        console.log(`Presenter_core: Disconnected from WebSocket. Code: ${event.code}, Reason: ${event.reason || 'No reason given'}, WasClean: ${event.wasClean}`); // DEBUG
        // Update main status and bottom indicator
        updateStatus(`已从服务器断开 (代码: ${event.code})。`, "error");

        // Clear any existing timer before starting a new one
        if (reconnectTimer) clearTimeout(reconnectTimer);

        // Attempt to reconnect after a delay, unless it was a clean close (code 1000)
        // or certain error codes where reconnecting might be futile (e.g., 1008 Policy Error, 1001 Going Away).
        if (event.code !== 1000 && event.code !== 1008 && event.code !== 1001) {
             console.log(`Presenter_core: Attempting to reconnect in ${reconnectDelay / 1000} seconds...`); // DEBUG
            reconnectTimer = setTimeout(connectWebSocket, reconnectDelay);
        } else {
             console.log(`Presenter_core: Disconnect code ${event.code}, not attempting reconnect.`);
        }

        // Signal external modules (like ui_utils) to reset UI states (e.g., re-enable buttons)
        // This is done by explicitly sending the 're_enable_auto_send_buttons' message
        // to the external handler, if it's set.
         if (externalMessageHandler) {
             console.log("Presenter_core: Dispatching re_enable_auto_send_buttons on disconnect.");
             externalMessageHandler('re_enable_auto_send_buttons', { message: "WebSocket已断开，请重新连接。" });
         } else {
              console.warn("Presenter_core: External message handler not set. Cannot signal UI to re-enable buttons on disconnect.");
         }
    };

    websocket.onerror = (error) => {
        console.error("Presenter_core: WebSocket Error:", error); // DEBUG
        // The 'error' event is often followed by the 'close' event.
        // The 'close' handler is responsible for attempting reconnection and updating status.
        // updateStatus("WebSocket连接错误。", "error"); // Status updated by onclose
    };
}

// Handle core-specific messages internally.
// Returns true if the message is *fully* handled by core and should *not* be passed to the external handler.
// Returns false if the message should also be passed to the external handler (e.g., registration_success).
function handleCoreMessage(messageType, data) {
     switch (messageType) {
         case "registration_success":
             // Core handles the initial status update (in onopen).
             // The message also needs to be passed to the external handler (in init.js)
             // so it can trigger initial state requests (browse_scripts, get_current_state).
             console.debug(`Presenter_core: Internal handling for registration_success.`);
             // Status update is done in onopen.
             return false; // Pass to external handler for feature initialization.


         case "pong":
             // Core handles the pong response for heartbeats.
             // No need to pass to external handler.
             // console.debug("Presenter_core: Received pong (internal)."); // Too noisy
             return true; // Fully handled internally.


         case "re_enable_auto_send_buttons":
             // This message is a signal for external logic (like button enabling in ui_utils).
             // Core doesn't have UI logic for this.
             // The message must be passed to the external handler, which should then call the relevant utility function.
             console.debug(`Presenter_core: Internal handling for re_enable_auto_send_buttons - dispatching externally.`);
             return false; // Pass to external handler.


         // Core doesn't need to explicitly handle generic info/warning/error messages here
         // if they are primarily for display by the external handler's updateStatus calls.
         // Just return false so they are dispatched.
         // case "info":
         // case "warning":
         // case "error":
         //    return false;


         default:
             // Any other message type is not a specific core message.
             // Return false so it's always passed to the external handler for feature logic.
             return false;
     }
}


// --- Initialization ---
// This runs when the DOM is fully loaded.
document.addEventListener('DOMContentLoaded', (event) => {
    console.log('Presenter_core: DOM fully loaded. Initializing WebSocket connection.'); // DEBUG

    // Assign references to the core status DOM elements.
    // These must exist in presenter_control.html with the correct IDs/classes.
    statusMessageDiv = document.getElementById('status-message');
    connectionStatusCircle = document.getElementById('connectionStatusCircle'); // Main status circle
    connectionStatusCircleFooter = document.getElementById('connectionStatusCircleFooter'); // Bottom circle
    statusTextFooter = document.querySelector('.status-text-footer'); // Bottom text footer text

    // Log acquisition status for core elements (helpful for debugging)
    console.log("Presenter_core: Core DOM Elements acquisition status:");
    console.log("statusMessageDiv:", statusMessageDiv ? "Found" : "Not Found");
    console.log("connectionStatusCircle:", connectionStatusCircle ? "Found" : "Not Found");
    console.log("connectionStatusCircleFooter:", connectionStatusCircleFooter ? "Found" : "Not Found");
    console.log("statusTextFooter:", statusTextFooter ? "Found" : "Not Found");


    // Start the WebSocket connection process.
    connectWebSocket();

    console.log("Presenter_core: DOMContentLoaded initialization complete.");
});


// --- Functions Exposed Globally ---
// These functions are made available to other JavaScript files loaded in the HTML.

// Expose sendMessage function so other modules can send messages via core.
window.sendMessage = sendMessage;
console.log("Presenter_core: Exposed window.sendMessage.");

// Expose updateStatus function so other modules can update the status display via core.
window.updateStatus = updateStatus;
console.log("Presenter_core: Exposed window.updateStatus.");

// Expose a way for presenter_init.js to provide its main message handler function.
// presenter_init.js should call window.presenterCore.setMessageHandler(handleServerMessage_from_init)
window.presenterCore = {
    setMessageHandler: function(handler) { // Define the setter function directly here
         if (typeof handler === 'function') {
              externalMessageHandler = handler; // Set the variable declared at the top
              console.log("Presenter_core: External message handler successfully set.");
         } else {
              console.error("Presenter_core: Attempted to set non-function as external message handler.");
              externalMessageHandler = null; // Ensure it's null if invalid handler is provided
         }
    },
    // Optional: Expose references to core status elements or functions if needed by other modules.
    // updateStatus is already exposed globally.
    // You could expose the websocket state like window.presenterCore.readyState = () => websocket ? websocket.readyState : WebSocket.CLOSED;
};
console.log("Presenter_core: Exposed window.presenterCore.setMessageHandler.");


console.log("presenter_core.js finished execution."); // This logs when the script finishes parsing/executing top-level code
