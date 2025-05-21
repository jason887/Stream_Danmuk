# flask_routes.py

from flask import Flask, jsonify, request, Blueprint # 在这里加上 Blueprint 的导入

import logging
import re

# Import necessary components from the database package
# Keep necessary imports from database facade and config
from database import get_db_manager, search_streamer_names, fetch_danmaku, fetch_reversal_copy_data, fetch_social_topics_data, fetch_anti_fan_quotes, db_config

# Import state manager getter
from state_manager import get_state_manager

# Global references to dependencies (will be set by init_flask_routes)
# _db_manager = None # REMOVED - Use get_db_manager() instead
_state_manager = None
_broadcast_message = None

# List to store streamer names for fuzzy search (loaded from DB on init)
_streamer_names_list = []


def init_flask_routes(db_manager_instance, state_manager_instance, broadcast_message_func):
    """
    Initializes Flask routes module with necessary dependencies.
    Fetches initial list of streamer names for search suggestions if DB is connected.
    Accepts db_manager_instance and state_manager_instance to ensure they are initialized,
    but stores only state_manager_instance and broadcast_message_func globally.
    DB access within routes will use get_db_manager().
    """
    logging.info("flask_routes: Initializing Flask routes module with dependencies.")
    global _state_manager, _broadcast_message, _streamer_names_list

    _state_manager = state_manager_instance
    _broadcast_message = broadcast_message_func

    # Fetch initial list of streamer names for the search suggestions
    # Use the database facade function, NOT the db_manager_instance directly for the query
    # Check if the instance is connected before attempting the fetch via facade
    if db_manager_instance and db_manager_instance.is_connected():
        try:
             # CALL THE FACADE FUNCTION HERE
             _streamer_names_list = search_streamer_names(term="", limit=0)
             logging.info(f"flask_routes: Loaded initial list of {len(_streamer_names_list)} streamer names for search suggestions.")
        except Exception as e:
            logging.error(f"flask_routes: Failed to load initial streamer names for search: {e}", exc_info=True)
            _streamer_names_list = [] # Ensure it's an empty list on failure
    else:
         # This warning should be less critical now as the DB connection is handled elsewhere
         # But it indicates the search suggestion list won't be pre-loaded.
         logging.warning("flask_routes: DB not connected during init. Streamer search suggestions may be unavailable.")
         _streamer_names_list = []


    logging.info("flask_routes: Flask routes module initialized.")


# Function to register routes on the Flask app instance
def register_flask_routes(app):
    """Registers the API endpoints with the provided Flask app instance."""
    logging.info("flask_routes: Registering Flask routes.")

    # Define Flask Blueprint
    api_bp = Blueprint('api', __name__, url_prefix='/api')


    # Helper to check DB connection
    def _is_db_connected():
        manager = get_db_manager()
        return manager and manager.is_connected()


    @api_bp.route('/search_streamers', methods=['GET'])
    def search_streamers():
        """Provides fuzzy search suggestions for streamer names."""
        term = request.args.get('term', '').strip()
        requester_addr = request.remote_addr

        if not _is_db_connected():
            logging.warning("flask_routes: API: DB not connected. Cannot perform streamer search.")
            # Return empty list for suggestions if DB is not connected, or 500 error?
            # Frontend might expect empty list for no suggestions. Let's return empty list.
            return jsonify([]) # Return empty list instead of 500 for search suggestions


        if not term:
            logging.debug("flask_routes: API: Search term is empty, returning empty list.")
            return jsonify([])

        try:
            # Perform search using the pre-loaded list (if available) or fallback to DB search
            if _streamer_names_list:
                 search_results = [name for name in _streamer_names_list if term.lower() in name.lower()]
                 logging.debug(f"flask_routes: API: Found {len(search_results)} matches in pre-loaded list for term '{term}'.")
                 return jsonify(search_results[:20])

            else:
                 logging.warning("flask_routes: API: Pre-loaded streamer list empty, attempting direct DB search for suggestions.")
                 # Use the database facade's search method - this is the intended path
                 db_search_results = search_streamer_names(term, limit=20) # Use facade function
                 logging.debug(f"flask_routes: API: Found {len(db_search_results)} matches in direct DB search for term '{term}'.")
                 return jsonify(db_search_results)


        except Exception as e:
            logging.error(f"flask_routes: API: Error during streamer search for term '{term}': {e}", exc_info=True)
            # On error, return empty list or an error response?
            # For search suggestions, returning empty list is often better UX than 500.
            return jsonify([]) # Return empty list on error



    # Keeping redundant routes but renaming to avoid clashes as before
    @api_bp.route('/api/search_streamer_names', methods=['GET'])
    def search_streamer_names_old():
        term = request.args.get('term', '').strip()
        if not _is_db_connected():
            return jsonify([])
        names = search_streamer_names(term, limit=20)
        return jsonify(names)

    @api_bp.route('/streamer_danmaku', methods=['GET'])
    def get_streamer_danmaku():
        name = request.args.get('name', '').strip()
        danmaku_type = request.args.get('type', '').strip().lower()
        requester_addr = request.remote_addr
        logging.info(f"flask_routes: API: Received streamer_danmaku request for name: '{name}', type: '{danmaku_type}' from {requester_addr}")

        if not _is_db_connected():
            logging.warning("flask_routes: API: DB not connected. Cannot fetch danmaku.")
            return jsonify({"error": "Database not connected."}), 500


        if not name or (danmaku_type not in ['welcome', 'roast']):
            logging.warning(f"flask_routes: API: Invalid request for streamer_danmaku: name='{name}', type='{danmaku_type}'")
            return jsonify({"error": "Invalid request. 'name' and valid 'type' ('welcome' or 'roast') are required."}), 400


        try:
            limit = 10
            # Use the database facade
            danmaku_list = fetch_danmaku(name, danmaku_type, limit=limit)

            if danmaku_list:
                 logging.info(f"flask_routes: API: Successfully returning {len(danmaku_list)} '{danmaku_type}' danmaku for streamer '{name}'.")
                 return jsonify(danmaku_list)
            else:
                logging.info(f"flask_routes: API: No '{danmaku_type}' danmaku found for streamer '{name}'. Returning empty list.")
                return jsonify([])


        except Exception as e:
            logging.error(f"flask_routes: API: Error fetching '{danmaku_type}' danmaku for '{name}': {e}", exc_info=True)
            return jsonify({"error": f"Error fetching {danmaku_type} danmaku."}), 500


    @api_bp.route('/streamer_reversal_copy', methods=['GET'])
    def get_streamer_reversal_copy():
        name = request.args.get('name', '').strip()
        requester_addr = request.remote_addr
        logging.info(f"flask_routes: API: Received streamer_reversal_copy request for name: '{name}' from {requester_addr}")

        if not _is_db_connected():
            logging.warning("flask_routes: API: DB not connected. Cannot fetch Reversal_Copy.")
            return jsonify({"error": "Database not connected."}), 500

        if not name:
            logging.warning("flask_routes: API: Invalid request for streamer_reversal_copy: name is empty.")
            return jsonify({"error": "'name' parameter is required."}), 400

        try:
            limit = 10
            # Use the database facade
            reversal_list = fetch_reversal_copy_data(name, limit)

            if reversal_list:
                 logging.info(f"flask_routes: API: Successfully fetched and returning {len(reversal_list)} Reversal_Copy entries for '{name}'.")
                 return jsonify(reversal_list)
            else:
                logging.info(f"flask_routes: API: No Reversal_Copy data found for streamer '{name}'. Returning empty list.")
                return jsonify([])


        except Exception as e:
            logging.error(f"flask_routes: API: Error fetching Reversal_Copy data for '{name}': {e}", exc_info=True)
            return jsonify({"error": "Error fetching Reversal_Copy data."}), 500


    @api_bp.route('/streamer_social_topics', methods=['GET'])
    def get_streamer_social_topics():
        name = request.args.get('name', '').strip()
        requester_addr = request.remote_addr
        logging.info(f"flask_routes: API: Received streamer_social_topics request for name/topic: '{name}' from {requester_addr}")

        if not _is_db_connected():
            logging.warning("flask_routes: API: DB not connected. Cannot fetch Social_Topics.")
            return jsonify({"error": "Database not connected."}), 500

        if not name:
            logging.warning("flask_routes: API: Invalid request for streamer_social_topics: name/topic is empty.")
            return jsonify({"error": "'name' (topic name) parameter is required."}), 400

        try:
            limit = 10
            # Use the database facade
            social_topics_list = fetch_social_topics_data(name, limit)

            if social_topics_list:
                 logging.info(f"flask_routes: API: Successfully fetched and returning {len(social_topics_list)} Social_Topics entries for topic '{name}'.")
                 return jsonify(social_topics_list)
            else:
                logging.info(f"flask_routes: API: No Social_Topics data found for topic '{name}'. Returning empty list.")
                return jsonify([])

        except Exception as e:
            logging.error(f"flask_routes: API: Error fetching Social_Topics data for topic '{name}': {e}", exc_info=True)
            return jsonify({"error": "Error fetching Social_Topics data."}), 500

    # Keeping redundant routes but renaming to avoid clashes
    @api_bp.route('/reversal_copy', methods=['GET'])
    def get_reversal_copy_old():
        name = request.args.get('name', '').strip()
        if not _is_db_connected():
            return jsonify({"error": "Database not connected."}), 500
        if not name:
            return jsonify([])
        try:
            # Use the database facade
            danmaku_list = fetch_danmaku(name, "reversal", limit=10) # Use facade function
            return jsonify(danmaku_list)
        except Exception as e:
            logging.error(f"API Error fetching reversal_copy (old route) for {name}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500

    # Keeping redundant routes but renaming to avoid clashes
    @api_bp.route('/generated_captions', methods=['GET'])
    def get_generated_captions_old():
        event = request.args.get('event', '').strip()
        if not _is_db_connected():
            return jsonify({"error": "Database not connected."}), 500
        if not event:
            return jsonify([])
        try:
             # Use the database facade
            danmaku_list = fetch_danmaku(event, "captions", limit=10) # Use facade function
            return jsonify(danmaku_list)
        except Exception as e:
            logging.error(f"API Error fetching generated_captions (old route) for {event}: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500


    @api_bp.route('/anti_fan_quotes', methods=['GET'])
    def get_anti_fan_quotes():
        """Fetches anti-fan quotes."""
        requester_addr = request.remote_addr
        logging.info(f"flask_routes: API: Received anti_fan_quotes request from {requester_addr}")

        if not _is_db_connected():
            logging.warning("flask_routes: API: DB not connected. Cannot fetch anti_fan_quotes.")
            return jsonify({"error": "Database not connected."}), 500

        try:
            limit = 3
            # Use the database facade
            quotes = fetch_anti_fan_quotes(limit=limit)

            if quotes:
                logging.info(f"flask_routes: API: Successfully returning {len(quotes)} anti_fan_quotes.")
                return jsonify(quotes)
            else:
                logging.info(f"flask_routes: API: No anti_fan_quotes found. Returning empty list.")
                return jsonify([])


        except Exception as e:
            logging.error(f"flask_routes: API: Error fetching anti_fan_quotes: {e}", exc_info=True)
            return jsonify({"error": "Error fetching anti-fan quotes."}), 500


    # Register the blueprint with the app
    app.register_blueprint(api_bp)


    logging.info("flask_routes: Flask routes registered.")


# Expose the necessary components for server.py
__all__ = [
    'init_flask_routes',
    'register_flask_routes',
]
