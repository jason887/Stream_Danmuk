# script_parser.py
import logging
import os

# Define an Event class or dictionary structure for parsed events
# Assuming each event has at least 'line' and 'prompt'
# Example structure: {"line": "这是要读的台词", "prompt": "这是给主播的提示"}

def parse_script_file(filepath):
    """
    Parses a simple text script file into a list of event dictionaries.
    Assumes each event is a single line in the text file.
    Lines starting with '#' are considered comments and are ignored.
    Empty lines are ignored.
    Each non-empty, non-comment line is treated as a single event's "line",
    with an empty "prompt" for simplicity in this basic parser.
    You can modify this parser based on your actual script file format.
    """
    events = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # Ignore comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Basic parsing: treat the whole line as the 'line' part, prompt is empty
                # Modify this logic if your script format is more complex (e.g., line | prompt)
                events.append({
                    "line": line,
                    "prompt": "", # Basic parser assumes no prompt in file line
                    # Add other metadata if needed, like original_line_num
                })

        logging.info(f"script_parser: Successfully parsed {len(events)} events from {filepath}")
        return events

    except FileNotFoundError:
        logging.error(f"script_parser: Script file not found: {filepath}")
        return []
    except Exception as e:
        logging.error(f"script_parser: Error parsing script file {filepath}: {e}", exc_info=True)
        return []

# Expose the main parsing function
__all__ = ['parse_script_file']
