# state_manager.py
import logging
import os # For path handling if needed later, though path handled in ws_script_handlers
try:
    from script_parser import parse_script_file # Assuming script_parser.py exists and works
except ImportError:
    logging.error("state_manager: Failed to import script_parser. Script parsing will be unavailable in state manager.")
    parse_script_file = None # Set to None if import fails


# Global instance of ApplicationStateManager
_state_manager_instance = None

class ApplicationStateManager:
    """Manages the global state of the application, such as loaded script and current event."""
    def __init__(self):
        logging.info("state_manager: Application state manager instance created.")
        self._script_filename = None
        self._script_content = [] # List of events from the parsed script
        self._current_event_index = -1 # -1 means no event selected yet or before the first event
        self._total_events = 0

        # State for roast sequence
        self._roast_target_name = None
        self._roast_templates = [] # List of raw string templates from DB
        self._current_roast_index = -1
        self._total_roasts = 0

        # Add new state variables
        self._roast_presenter_cue = ""
        self._roast_raw_template = ""
        self._roast_danmaku_sent = ""

        logging.info("state_manager: Application state initialized.")

    def load_script(self, script_full_path):
        """
        Parses a script file and loads its content into the state.
        Resets current event index.
        Returns True on success, False on failure.
        """
        if not os.path.exists(script_full_path):
            logging.error(f"state_manager: Script file not found: {script_full_path}")
            self._script_filename = None
            self._script_content = []
            self._current_event_index = -1
            self._total_events = 0
            return False

        if parse_script_file is None:
             logging.error("state_manager: script_parser is not available. Cannot load script.")
             self._script_filename = None
             self._script_content = []
             self._current_event_index = -1
             self._total_events = 0
             return False


        try:
            # Use the imported parse_script_file function
            parsed_events = parse_script_file(script_full_path)

            # Update state with loaded script
            self._script_filename = os.path.basename(script_full_path)
            self._script_content = parsed_events # Assuming parse_script_file returns a list of event objects/dicts
            self._total_events = len(self._script_content)
            self._current_event_index = -1 # Reset to before the first event on load

            logging.info(f"state_manager: Script loaded successfully: '{self._script_filename}' with {self._total_events} events.")
            return True

        except Exception as e:
            logging.error(f"state_manager: Error loading or parsing script '{script_full_path}': {e}", exc_info=True)
            self._script_filename = None
            self._script_content = []
            self._current_event_index = -1
            self._total_events = 0
            return False


    def get_current_event(self):
        """Returns the current event object/dict, or None if no script is loaded or index is invalid."""
        if not self._script_content or self._current_event_index < 0 or self._current_event_index >= self._total_events:
            return None
        return self._script_content[self._current_event_index]

    def advance_roast_sequence(self, processed_danmaku, presenter_line, raw_template): 
        """Advances the roast sequence to the next item and updates presenter display info.""" 
        if self._roast_target_name is None: 
            logging.warning("state_manager: Attempted to advance roast sequence, but not in roast mode.") 
            return None 

        current_index = self._current_roast_index + 1 
        total_templates = len(self._roast_templates) 

        if current_index >= total_templates: 
            logging.info(f"state_manager: Roast sequence for '{self._roast_target_name}' finished. Index {current_index} out of bounds {total_templates}.") 
            self.exit_roast_sequence() 
            return False 

        self._current_roast_index = current_index 
        self._roast_danmaku_sent = processed_danmaku
        self._roast_presenter_cue = presenter_line 
        self._roast_raw_template = raw_template 

        logging.debug(f"state_manager: Advanced roast sequence to index {current_index}. Total: {total_templates}. Target: {self._roast_target_name}") 
        self._log_state() 

        return True 

    def get_current_state(self):
        """Returns the current application state."""
        current_event = self.get_current_event()
        state_to_return = {
            "script_filename": self._script_filename,
            "total_events": self._total_events,
            "event_index": self._current_event_index,
            "current_line": current_event.get("line") if current_event else "" if self._roast_target_name is None else "",
            "current_prompt": current_event.get("prompt") if current_event else "" if self._roast_target_name is None else "",
            "is_roast_mode": self._roast_target_name is not None,
            "current_roast_index": self._current_roast_index,
            "total_roasts": self._total_roasts,
            "current_roast_target": self._roast_target_name,
            "roast_presenter_cue": self._roast_presenter_cue if self._roast_target_name is not None else "",
            "roast_raw_template": self._roast_raw_template if self._roast_target_name is not None else "",
            "roast_danmaku_sent": self._roast_danmaku_sent if self._roast_target_name is not None else "",
        }

        return state_to_return

    def advance_event(self):
        """Moves to the next event in the script. Returns the new index or -1 if finished."""
        if not self._script_content:
            return -1 # No script loaded

        # Increment index
        new_index = self._current_event_index + 1

        # Check if we are at or past the last event
        if new_index >= self._total_events:
            self._current_event_index = self._total_events # Cap index at total_events to indicate finish
            logging.info(f"state_manager: Reached end of script: '{self._script_filename}'.")
            return self._total_events # Return total events to signal end

        self._current_event_index = new_index
        logging.info(f"state_manager: Advanced to event index: {self._current_event_index} / {self._total_events - 1}.")
        return self._current_event_index

    def prev_event(self):
        """Moves to the previous event in the script. Returns the new index or -1 if already at the beginning."""
        if not self._script_content:
            return -1 # No script loaded

        # Decrement index
        new_index = self._current_event_index - 1

        # Check if we are before the first event
        if new_index < -1: # Allow going back to -1
             new_index = -1

        self._current_event_index = new_index
        logging.info(f"state_manager: Moved to previous event index: {self._current_event_index} / {self._total_events - 1}.")
        return self._current_event_index

    # --- Roast Sequence Management ---
    def start_roast_sequence(self, target_name, templates_list):
        """Initializes the roast sequence state."""
        if not templates_list:
            logging.warning("state_manager: Attempted to start roast sequence with no templates.")
            self._roast_target_name = None
            self._roast_templates = []
            self._current_roast_index = -1
            self._total_roasts = 0
            return False

        logging.info(f"state_manager: Roast sequence started for target '{target_name}' with {len(templates_list)} templates.")
        
        # 存储完整的模板列表和目标名称
        self._roast_target_name = target_name
        self._roast_templates = templates_list
        self._current_roast_index = -1
        self._total_roasts = len(templates_list)

        # 清空当前显示相关的状态
        self._script_filename = None
        self._script_content = []
        self._current_event_index = -1
        self._total_events = 0

        return True


    def get_next_roast_template(self):
        """
        Increments the roast index and returns the template parts for the new index.
        Returns (danmaku_part, presenter_part, raw_template, current_num, total_num)
        or (None, None, None, total_num, total_num) if sequence finished.
        """
        if self._roast_target_name is None or not self._roast_templates:
            logging.warning("state_manager: Attempted to get next roast template, but no sequence is active.")
            return None, None, None, -1, 0 # No sequence active

        # Increment the index
        self._current_roast_index += 1

        # Check if the sequence has finished
        if self._current_roast_index >= self._total_roasts:
             logging.info(f"state_manager: Roast sequence for '{self._roast_target_name}' finished. Index {self._current_roast_index} out of bounds {self._total_roasts}.")
             # Optionally reset state here or let exit_roast_mode handle it
             # self.exit_roast_sequence() # Let exit_roast_sequence handle cleanup
             return None, None, None, self._total_roasts, self._total_roasts # Signal finish

        # Get the current template string
        raw_template = self._roast_templates[self._current_roast_index]
        logging.debug(f"state_manager: Getting roast template at index {self._current_roast_index}: '{raw_template}'")

        # Split the template into danmaku and presenter parts using the last comma (，)
        # Use rfind to find the last occurrence of the fullwidth comma
        last_comma_index = raw_template.rfind('，')

        if last_comma_index != -1:
            danmaku_part_template = raw_template[:last_comma_index].strip()
            presenter_part = raw_template[last_comma_index + 1:].strip()
        else:
             # If no comma found, use the whole string as presenter part and no danmaku (or handle as error)
             # Let's define behavior: If no comma, treat the whole string as presenter part
            danmaku_part_template = "" # No danmaku part if no comma
            presenter_part = raw_template.strip() # Whole string is the presenter part
            logging.warning(f"state_manager: Roast template has no fullwidth comma '，': '{raw_template}'. Treating whole string as presenter part.")


        # Replace {} in danmaku_part_template with the target name
        danmaku_part = danmaku_part_template.replace("{}", self._roast_target_name)

        # Return parts and current progress
        return danmaku_part, presenter_part, raw_template, self._current_roast_index + 1, self._total_roasts


    def exit_roast_sequence(self):
        """Resets roast sequence state and potentially restores script state."""
        if self._roast_target_name is not None:
            logging.info(f"state_manager: Exiting roast sequence for target '{self._roast_target_name}'.")
            self._roast_templates = []
            self._roast_target_name = None
            self._current_roast_index = -1
            # 对应 _app_state['is_roast_mode']
            # 由于类中没有直接对应的变量，这里不需要设置
            # 但在 get_current_state 中会根据 _roast_target_name 判断
            self._roast_presenter_cue = ""
            self._roast_raw_template = ""
            self._roast_danmaku_sent = ""
            self._log_state()  # Log current state
            return True  # Indicate sequence was active and is now exited
        return False  # Indicate no sequence was active


# Function to be called by server.py to initialize the instance and set module global
def init_state_manager(manager_instance):
    """Sets the module-level global instance of ApplicationStateManager."""
    global _state_manager_instance
    _state_manager_instance = manager_instance
    logging.info("state_manager: Module-level instance initialized.")


# Function for other modules to get the initialized instance
def get_state_manager():
    """Returns the module-level global instance of ApplicationStateManager."""
    if _state_manager_instance is None:
        logging.error("state_manager: ApplicationStateManager instance has not been initialized. Call init_state_manager first.")
        # For this application structure, it should always be initialized by server.py startup
        # Depending on usage, you might want to raise an error here instead of returning None
    return _state_manager_instance


# Expose the necessary components for server.py and other modules
__all__ = [
    'ApplicationStateManager', # Expose the class itself
    'init_state_manager',      # Expose the initialization function
    'get_state_manager',       # Expose the getter function
]

